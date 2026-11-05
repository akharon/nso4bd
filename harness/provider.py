"""Model-provider abstraction, so the same grid can run on any vendor.

Plan rev. 2 sec. 6.4 asks for at least one evaluated model from a different
family than the one that authored the corpus. Model-written code may be
unusually legible to its own family, and the treatments depend on inferring
roles from variable names -- exactly the signal an author and evaluator from
one family would share. A second vendor is therefore a control, not just a
convenience.

Providers are normalized to one call returning a Reply, so nothing downstream
(blinding, scoring, analysis) needs to know which vendor produced a
transcript. In particular `truncated` is normalized: Anthropic reports
stop_reason == "max_tokens", OpenAI-compatible APIs report
finish_reason == "length". Getting that mapping wrong would silently
reintroduce the truncation artifact of plan sec. 7.3.

Selection is by model name, or forced with --provider.

  anthropic : ANTHROPIC_API_KEY   claude-*
  deepseek  : DEEPSEEK_API_KEY    deepseek-*   (OpenAI-compatible)
  openai    : OPENAI_API_KEY      gpt-*
"""

import os
import sys

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class Reply(object):
    """One normalized model response."""

    def __init__(self, text, input_tokens, output_tokens, stop_reason,
                 truncated):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.stop_reason = stop_reason
        self.truncated = truncated


def provider_for(model, override=None):
    if override:
        return override
    name = (model or "").lower()
    if name.startswith("deepseek"):
        return "deepseek"
    if name.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return "anthropic"


ENV_VAR = {
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
}

PACKAGE = {
    "anthropic": "anthropic",
    "deepseek": "openai",
    "openai": "openai",
}


class Client(object):
    def __init__(self, model, provider=None):
        self.model = model
        self.provider = provider_for(model, provider)

        env = ENV_VAR[self.provider]
        if not os.environ.get(env, "").strip():
            raise RuntimeError(
                "%s is not set. Export it and re-run.\n"
                "  provider resolved to '%s' from model '%s'"
                % (env, self.provider, model))

        pkg = PACKAGE[self.provider]
        try:
            if self.provider == "anthropic":
                import anthropic
                self._client = anthropic.Anthropic()
            else:
                import openai
                kwargs = {"api_key": os.environ[env]}
                if self.provider == "deepseek":
                    kwargs["base_url"] = DEEPSEEK_BASE_URL
                self._client = openai.OpenAI(**kwargs)
        except ImportError:
            raise RuntimeError(
                "The '%s' package is not installed.\n"
                "Install it with:  pip install %s" % (pkg, pkg))

    def complete(self, prompt, max_tokens, temperature):
        if self.provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in resp.content
                           if getattr(b, "type", None) == "text")
            return Reply(
                text=text,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                stop_reason=resp.stop_reason,
                # Anthropic signals a hit token cap as stop_reason.
                truncated=(resp.stop_reason == "max_tokens"),
            )

        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        choice = resp.choices[0]
        finish = choice.finish_reason
        usage = resp.usage
        return Reply(
            text=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            stop_reason=finish,
            # OpenAI-compatible APIs say "length" for the same condition.
            truncated=(finish == "length"),
        )
