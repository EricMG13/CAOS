async def get_identity(
    request: Request, db: AsyncSession = Depends(get_db, scope="function")
) -> CallerIdentity:
    """Resolve a verified profile, proxy principal, or development identity."""
    settings = get_settings()
    deployed = is_deployed(settings)

    # Every deployed request proves edge transit before any identity is trusted.
    if deployed and settings.edge_proxy_secret:
        presented = request.headers.get("x-edge-authorization", "")
        if not hmac.compare_digest(
            presented.encode("utf-8", "ignore"),
            settings.edge_proxy_secret.encode("utf-8"),
        ):
            raise HTTPException(401, "Request did not carry a valid edge credential.")

    token = request.cookies.get(COOKIE_NAME)
    if token:
        data = read_session_token(token, settings.session_secret)
        if data and data.get("id") and data.get("name"):
            analyst_id = sanitize_field(data["id"])
            analyst = await db.get(Analyst, analyst_id)
            if analyst is not None and analyst.token_version == data.get("v", 0):
                cookie_email = sanitize_field(data.get("email", ""))
                forwarded_email = request.headers.get("x-forwarded-email")
                same_principal = (
                    not deployed
                    or not forwarded_email
                    or cookie_email.lower() == forwarded_email.strip().lower()
                )
                if same_principal:
                    return CallerIdentity(
                        id=analyst_id,
                        email=cookie_email,
                        full_name=sanitize_field(data["name"]),
                        role=getattr(analyst, "role", None) or "analyst",
                        source="profile",
                        team_id=analyst.team_id,
                    )

    email = request.headers.get("x-forwarded-email")
    user = request.headers.get("x-forwarded-user")
    if not email and not user:
        if deployed:
            raise HTTPException(
                401,
                "No forwarded identity — request did not pass the auth proxy / edge.",
            )
        return _LOCAL_DEV

    persisted_analyst = None
    if email and hasattr(db, "execute"):
        persisted_analyst = (
            await db.execute(
                select(Analyst).where(func.lower(Analyst.email) == email.strip().lower())
            )
        ).scalar_one_or_none()

    username = request.headers.get("x-forwarded-preferred-username") or email or user
    return CallerIdentity(
        id=sanitize_field(user or email or "unknown"),
        email=sanitize_field(email or user or "unknown"),
        full_name=sanitize_field(username or "Authenticated User"),
        role=getattr(persisted_analyst, "role", None) or "analyst",
        source="proxy",
        team_id=persisted_analyst.team_id if persisted_analyst is not None else None,
    )
