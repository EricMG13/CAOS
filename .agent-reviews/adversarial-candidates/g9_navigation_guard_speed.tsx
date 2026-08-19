export function NavigationGuardProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const registrations = useRef(new Map<symbol, GuardRegistration>());
  const pendingRef = useRef<PendingNavigation | null>(null);
  const [pending, setPending] = useState<PendingNavigation | null>(null);
  const [activeGuardCount, setActiveGuardCount] = useState(0);

  // Collect in one pass rather than Array.from(...).filter(...). Guard order is
  // still Map insertion order, which is the discard-callback contract.
  const activeGuards = useCallback(() => {
    const guards: GuardRegistration[] = [];
    for (const guard of registrations.current.values()) {
      if (guard.enabled && guard.dirty) guards.push(guard);
    }
    return guards;
  }, []);

  // Counting registrations does not need to allocate a guard snapshot.
  const syncActiveCount = useCallback(() => {
    let count = 0;
    for (const guard of registrations.current.values()) {
      if (guard.enabled && guard.dirty) count += 1;
    }
    setActiveGuardCount(count);
  }, []);

  const registerGuard = useCallback(
    (id: symbol, registration: GuardRegistration) => {
      registrations.current.set(id, registration);
      syncActiveCount();
      return () => {
        const current = registrations.current;
        if (current.get(id) === registration) current.delete(id);
        syncActiveCount();
      };
    },
    [syncActiveCount],
  );

  // The optional internal snapshot lets click interception collect active guards
  // once. The context still exposes the exact one-argument attemptNavigation type.
  const queueAttempt = useCallback(
    (proceed: () => void, guards: GuardRegistration[] = activeGuards()): boolean => {
      if (guards.length === 0) {
        proceed();
        return true;
      }
      if (pendingRef.current) return false;
      const request = { proceed, guards };
      pendingRef.current = request;
      setPending(request);
      return false;
    },
    [activeGuards],
  );

  const stay = useCallback(() => {
    pendingRef.current = null;
    setPending(null);
  }, []);

  const discardAndLeave = useCallback(() => {
    const request = pendingRef.current;
    if (!request) return;
    pendingRef.current = null;
    setPending(null);
    for (const guard of request.guards) {
      try {
        guard.onDiscard();
      } catch {
        // A faulty synchronous discard cannot trap a user who chose to leave.
      }
    }
    request.proceed();
  }, []);

  useEffect(() => {
    if (activeGuardCount === 0) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [activeGuardCount]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const guards = activeGuards();
      if (guards.length === 0) return;
      const element =
        event.target instanceof Element
          ? event.target.closest<HTMLAnchorElement>("a[href]")
          : null;
      if (!element || element.hasAttribute("download")) return;
      if (element.target && element.target.toLowerCase() !== "_self") return;
      const url = new URL(element.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      queueAttempt(
        () => router.push(`${url.pathname}${url.search}${url.hash}`),
        guards,
      );
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [activeGuards, queueAttempt, router]);

  useEffect(() => {
    const history = window.history;
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    const initialState = history.state;
    const originalIndex = historyIndex(initialState) ?? 0;
    const currentIndex = { value: originalIndex };
    originalReplaceState.call(
      history,
      withHistoryIndex(initialState, originalIndex),
      "",
      window.location.href,
    );

    const wrappedPushState: History["pushState"] = (data, unused, url) => {
      const next = currentIndex.value + 1;
      currentIndex.value = next;
      return originalPushState.call(
        history,
        withHistoryIndex(data, next),
        unused,
        url,
      );
    };
    const wrappedReplaceState: History["replaceState"] = (data, unused, url) =>
      originalReplaceState.call(
        history,
        withHistoryIndex(data, currentIndex.value),
        unused,
        url,
      );
    history.pushState = wrappedPushState;
    history.replaceState = wrappedReplaceState;

    let allowNextPop = false;
    let bounce: {
      origin: number;
      delta: number;
      guards: GuardRegistration[];
    } | null = null;
    const onPopState = (event: PopStateEvent) => {
      const destination = historyIndex(event.state);
      if (allowNextPop) {
        allowNextPop = false;
        if (destination != null) currentIndex.value = destination;
        return;
      }
      if (bounce) {
        const resumed = bounce;
        bounce = null;
        currentIndex.value = resumed.origin;
        if (!pendingRef.current) {
          const request: PendingNavigation = {
            guards: resumed.guards,
            proceed: () => {
              allowNextPop = true;
              history.go(resumed.delta);
            },
          };
          pendingRef.current = request;
          setPending(request);
        }
        return;
      }

      const delta = destination == null ? -1 : destination - currentIndex.value;
      if (delta === 0) return;
      const guards = activeGuards();
      if (guards.length === 0) {
        if (destination != null) currentIndex.value = destination;
        return;
      }
      bounce = { origin: currentIndex.value, delta, guards };
      history.go(-delta);
    };
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("popstate", onPopState);
      if (history.pushState === wrappedPushState) history.pushState = originalPushState;
      if (history.replaceState === wrappedReplaceState) {
        history.replaceState = originalReplaceState;
      }
    };
  }, [activeGuards]);

  const value = useMemo<NavigationGuardContextValue>(
    () => ({ registerGuard, attemptNavigation: queueAttempt }),
    [queueAttempt, registerGuard],
  );

  return (
    <NavigationGuardContext.Provider value={value}>
      {children}
      {pending ? (
        <NavigationConfirmDialog onStay={stay} onDiscard={discardAndLeave} />
      ) : null}
    </NavigationGuardContext.Provider>
  );
}
