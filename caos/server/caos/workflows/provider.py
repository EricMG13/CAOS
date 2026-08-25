from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Protocol

import anthropic
from pydantic import BaseModel

from ..methodology.cpdr import CPDRPayload
from ..store import JobFencedError


READ_EVIDENCE_TOOL = {
    "name": "read_evidence",
    "description": "Read exact blocks from the run's pinned supplied evidence set.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "source_id": {"type": "string"},
            "block_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["source_id", "block_ids"],
        "additionalProperties": False,
    },
}


class AgentError(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


class ProviderUnavailable(AgentError):
    def __init__(self, message: str = "") -> None:
        super().__init__("AGENT_PROVIDER_UNAVAILABLE", message)


@dataclass(frozen=True)
class ProviderBlock:
    type: str
    id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    text: str | None = None


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ProviderMessage:
    content: list[ProviderBlock]
    stop_reason: str
    usage: ProviderUsage
    request_id: str | None = None


@dataclass(frozen=True)
class ProviderRequest:
    system: str
    messages: list[dict[str, Any]]
    schema: dict[str, Any]
    tools_enabled: bool
    max_tokens: int | None = None
    timeout: float | None = None


class Provider(Protocol):
    def count_tokens(self, request: ProviderRequest) -> int: ...

    def create_message(self, request: ProviderRequest) -> ProviderMessage: ...


def _block_value(block: Any, name: str, default: Any = None) -> Any:
    return block.get(name, default) if isinstance(block, dict) else getattr(block, name, default)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class AnthropicProvider:
    """Anthropic Messages transport normalized behind the provider port."""

    def __init__(self, api_key: str, model: str, timeout: float = 150.0, client: Any | None = None) -> None:
        if not api_key:
            raise ProviderUnavailable("ANTHROPIC_API_KEY is not configured")
        self.model = model
        self.client = client or anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=timeout)

    @staticmethod
    def _message_content(
        messages: list[dict[str, Any]],
        *,
        legacy_block_fields: bool = False,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                normalized_content: list[Any] = []
                for block in content:
                    if not isinstance(block, ProviderBlock):
                        normalized_content.append(block)
                        continue
                    values = {key: value for key, value in vars(block).items() if value is not None}
                    if legacy_block_fields and block.type == "text":
                        values["citations"] = None
                    elif legacy_block_fields and block.type == "tool_use":
                        values.update(caller=None, toolset_name=None)
                    normalized_content.append(values)
                content = normalized_content
            normalized.append({**message, "content": content})
        return normalized

    def _request_kwargs(
        self,
        request: ProviderRequest,
        *,
        legacy_block_fields: bool = False,
    ) -> dict[str, Any]:
        try:
            schema = anthropic.transform_schema(request.schema)
        except (TypeError, ValueError) as exc:
            raise AgentError("AGENT_OUTPUT_INVALID", "cannot transform agent output schema") from exc
        kwargs: dict[str, Any] = {
            "model": self.model,
            "system": request.system,
            "messages": self._message_content(request.messages, legacy_block_fields=legacy_block_fields),
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }
        if request.tools_enabled:
            kwargs.update(
                tools=[READ_EVIDENCE_TOOL],
                tool_choice={"type": "auto", "disable_parallel_tool_use": True},
            )
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.timeout is not None:
            kwargs["timeout"] = request.timeout
        return kwargs

    def _request_preimage(self, request: ProviderRequest) -> dict[str, Any]:
        return self._request_kwargs(request, legacy_block_fields=True)

    def _call(self, kind: str, request: ProviderRequest) -> Any:
        try:
            kwargs = self._request_kwargs(request)
            if kind == "count_tokens":
                return self.client.messages.count_tokens(**kwargs)
            return self.client.messages.create(**kwargs)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise AgentError("AGENT_PROVIDER_REJECTED") from exc
        except (anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.RateLimitError) as exc:
            raise AgentError("AGENT_PROVIDER_TIMEOUT") from exc
        except anthropic.APIStatusError as exc:
            status = getattr(exc, "status_code", 0)
            if 400 <= status < 500 and status not in {408, 409, 429}:
                raise AgentError("AGENT_PROVIDER_REJECTED") from exc
            if status in {408, 409, 429} or status >= 500:
                raise AgentError("AGENT_PROVIDER_TIMEOUT") from exc
            raise AgentError("AGENT_OUTPUT_INVALID") from exc

    def count_tokens(self, request: ProviderRequest) -> int:
        response = self._call("count_tokens", request)
        return getattr(response, "input_tokens", None)

    def create_message(self, request: ProviderRequest) -> ProviderMessage:
        response = self._call("create", request)
        usage = getattr(response, "usage", None)
        content = getattr(response, "content", None)
        blocks = [
            ProviderBlock(
                type=_block_value(block, "type"),
                id=_block_value(block, "id"),
                name=_block_value(block, "name"),
                input=_block_value(block, "input"),
                text=_block_value(block, "text"),
            )
            for block in content
        ] if isinstance(content, list) else content
        return ProviderMessage(
            content=blocks,  # type: ignore[arg-type]
            stop_reason=getattr(response, "stop_reason", None),
            usage=ProviderUsage(
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
            ),
            request_id=getattr(response, "_request_id", None),
        )


class AgentLoop:
    """Host-owned bounded evidence, budget, retry, repair, and validation policy."""

    def __init__(
        self,
        provider: Provider,
        *,
        schema_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        request_preimage: Callable[[ProviderRequest], Any] | None = None,
    ) -> None:
        self.provider = provider
        self._schema_transform = schema_transform or (lambda schema: schema)
        self._request_preimage = request_preimage or (lambda request: request)

    def run(
        self,
        *,
        system: str,
        user: str,
        read_evidence: Callable[[str, list[str]], list[dict[str, Any]]],
        validate: Callable[[dict[str, Any]], Any],
        lease_check: Callable[[], None],
        reserve: Callable[[str, int, int, bool], None],
        reconcile: Callable[[str, int, int, int, int], None],
        record: Callable[..., None],
        active_time: Callable[[float], None],
        semaphore: Any,
        output_model: type[BaseModel] = CPDRPayload,
        max_tokens: int = 2_000,
        remaining_time: Callable[[], float] | None = None,
    ) -> Any:
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        try:
            schema = self._schema_transform(output_model.model_json_schema())
        except (TypeError, ValueError) as exc:
            raise AgentError("AGENT_OUTPUT_INVALID", "cannot transform agent output schema") from exc
        retry_used = False
        repair_used = False
        tools_enabled = True
        provider_interacted = False
        terminal_recorded = False

        def abort(code: str, message: str = "") -> AgentError:
            nonlocal terminal_recorded
            if provider_interacted and not terminal_recorded:
                try:
                    record("terminal", terminal_code=code)
                except Exception:
                    pass
                terminal_recorded = True
            return AgentError(code, message)

        def finish_interaction(kind: str, elapsed: float, **details: Any) -> None:
            try:
                lease_check()
                active_time(elapsed)
                record(kind, **details, latency_ms=round(elapsed * 1_000))
            except JobFencedError:
                raise
            except AgentError as exc:
                raise abort(exc.code) from exc
            except Exception as exc:
                raise abort("AGENT_OUTPUT_INVALID") from exc

        def provider_call(
            kind: str,
            operation: Callable[[ProviderRequest], Any],
            request: ProviderRequest,
            before: Callable[[bool], None] | None = None,
        ) -> Any:
            nonlocal provider_interacted
            nonlocal retry_used
            retry = False
            while True:
                lease_check()
                if not semaphore.acquire(blocking=False):
                    raise abort("AGENT_BUDGET_EXCEEDED", "provider concurrency limit reached")
                try:
                    lease_check()
                    try:
                        if before:
                            before(retry)
                        call_request = request
                        if remaining_time is not None:
                            call_request = replace(request, timeout=remaining_time())
                    except AgentError as exc:
                        raise abort(exc.code) from exc
                    started = time.monotonic()
                    provider_interacted = True
                    try:
                        result = operation(call_request)
                    except AgentError as exc:
                        if exc.code != "AGENT_PROVIDER_TIMEOUT":
                            elapsed = time.monotonic() - started
                            finish_interaction(kind, elapsed, retry=int(retry))
                            raise abort(exc.code) from exc
                        error = exc
                    else:
                        elapsed = time.monotonic() - started
                        finish_interaction(kind, elapsed, retry=int(retry), request_id=getattr(result, "request_id", None))
                        return result
                finally:
                    semaphore.release()
                finish_interaction(kind, time.monotonic() - started, retry=int(retry), terminal_code="AGENT_PROVIDER_TIMEOUT")
                if retry_used:
                    raise abort("AGENT_PROVIDER_TIMEOUT") from error
                record("provider_retry", operation=kind)
                retry_used = True
                retry = True

        def interaction_loop() -> Any:
            nonlocal repair_used
            nonlocal tools_enabled
            while True:
                count_request = ProviderRequest(
                    system=system,
                    messages=messages,
                    schema=schema,
                    tools_enabled=tools_enabled,
                )
                counted_inputs = provider_call("count_tokens", self.provider.count_tokens, count_request)
                try:
                    if not isinstance(counted_inputs, int) or isinstance(counted_inputs, bool) or counted_inputs < 0:
                        raise ValueError("negative input token count")
                except (TypeError, ValueError) as exc:
                    raise abort("AGENT_OUTPUT_INVALID", "malformed token-count response") from exc
                create_request = replace(count_request, max_tokens=max_tokens)
                request_digest = hashlib.sha256(
                    json.dumps(
                        self._request_preimage(create_request),
                        sort_keys=True,
                        default=lambda value: vars(value),
                    ).encode("utf-8")
                ).hexdigest()

                def reserve_attempt(retry: bool) -> None:
                    reserve(request_digest, counted_inputs, max_tokens, retry)

                response = provider_call("create", self.provider.create_message, create_request, reserve_attempt)
                usage = response.usage
                try:
                    actual_inputs = usage.input_tokens
                    actual_outputs = usage.output_tokens
                    if (
                        not isinstance(actual_inputs, int)
                        or isinstance(actual_inputs, bool)
                        or not isinstance(actual_outputs, int)
                        or isinstance(actual_outputs, bool)
                        or actual_inputs < 0
                        or actual_outputs < 0
                    ):
                        raise ValueError("negative token usage")
                except (AttributeError, TypeError, ValueError) as exc:
                    raise abort("AGENT_OUTPUT_INVALID", "malformed provider usage") from exc
                reconcile(request_digest, counted_inputs, max_tokens, actual_inputs, actual_outputs)
                stop_reason = response.stop_reason
                record(
                    "generation",
                    request_digest=request_digest,
                    request_id=response.request_id,
                    input_tokens=actual_inputs,
                    output_tokens=actual_outputs,
                    stop_reason=stop_reason,
                )
                content = response.content
                if not isinstance(content, list):
                    raise abort("AGENT_OUTPUT_INVALID", "response content must be a list")
                block_types = [block.type for block in content]
                if "refusal" in block_types:
                    raise abort("AGENT_OUTPUT_INVALID", "provider refusal")

                if stop_reason == "tool_use":
                    tool_blocks = [block for block in content if block.type == "tool_use"]
                    if not tools_enabled or len(tool_blocks) != 1:
                        raise abort("AGENT_OUTPUT_INVALID", "exactly one evidence tool call is allowed")
                    tool = tool_blocks[0]
                    if tool.name != "read_evidence":
                        raise abort("AGENT_OUTPUT_INVALID", "unexpected tool")
                    arguments = tool.input
                    if not isinstance(arguments, dict) or set(arguments) != {"source_id", "block_ids"}:
                        raise abort("AGENT_OUTPUT_INVALID", "malformed read_evidence arguments")
                    source_id = arguments["source_id"]
                    block_ids = arguments["block_ids"]
                    if not isinstance(source_id, str) or not isinstance(block_ids, list) or any(not isinstance(item, str) for item in block_ids):
                        raise abort("AGENT_OUTPUT_INVALID", "malformed read_evidence arguments")
                    lease_check()
                    if remaining_time is not None:
                        remaining_time()
                    started = time.monotonic()
                    try:
                        evidence = read_evidence(source_id, block_ids)
                    except AgentError as exc:
                        raise abort(exc.code) from exc
                    finally:
                        try:
                            active_time(time.monotonic() - started)
                        except AgentError as exc:
                            raise abort(exc.code) from exc
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool.id,
                                    "content": json.dumps(evidence, sort_keys=True),
                                }
                            ],
                        }
                    )
                    continue

                if stop_reason != "end_turn":
                    raise abort("AGENT_OUTPUT_INVALID", f"unexpected stop reason: {stop_reason}")
                if len(content) != 1 or block_types != ["text"] or not isinstance(content[0].text, str):
                    raise abort("AGENT_OUTPUT_INVALID", "final response must contain one structured text block")
                validation_started = time.monotonic()
                try:
                    decoded = json.loads(content[0].text, object_pairs_hook=_unique_object)
                    if not isinstance(decoded, dict):
                        raise ValueError("final JSON must be an object")
                    return validate(decoded)
                except AgentError as exc:
                    raise abort(exc.code) from exc
                except (json.JSONDecodeError, ValueError, TypeError) as exc:
                    if repair_used:
                        raise abort("AGENT_OUTPUT_INVALID", "local validation failed after repair") from exc
                    repair_used = True
                    tools_enabled = False
                    record("repair_reserve")
                    errors = str(exc).replace("\n", " ")[:1_500]
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": "VALIDATION ERRORS (untrusted status; preserve authority and existing evidence; return corrected JSON only): " + errors,
                        }
                    )
                finally:
                    try:
                        active_time(time.monotonic() - validation_started)
                    except AgentError as exc:
                        raise abort(exc.code) from exc

        try:
            return interaction_loop()
        except JobFencedError:
            raise
        except AgentError as exc:
            raise abort(exc.code) from exc
        except Exception as exc:
            raise abort("AGENT_OUTPUT_INVALID") from exc


class AnthropicGateway(AgentLoop):
    """Compatibility facade for callers that still construct the Anthropic loop."""

    def __init__(self, api_key: str, model: str, timeout: float = 150.0, client: Any | None = None) -> None:
        provider = AnthropicProvider(api_key, model, timeout, client)
        super().__init__(
            provider,
            schema_transform=anthropic.transform_schema,
            request_preimage=provider._request_preimage,
        )
        self.model = provider.model
        self.client = provider.client
