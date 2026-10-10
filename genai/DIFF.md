---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0 (opentelemetry-sdk 1.45.0, openai 3.19.2)"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.top_p, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.request.seed, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.request.stop_sequences, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.request.frequency_penalty, emitted: false, in_spec: true, stability: development}
---
<!-- ai-generated: 50% - Claude Code ran the call and checked the registry; the reading of the differences is drafted with it and reviewed by me -->

# What the library emits, against the spec

I made one chat completion through the OpenAI client against a local Ollama model (`qwen3:1.7b`, OpenAI-compatible
endpoint on `localhost:11434/v1`), with `OpenAIInstrumentor` from `opentelemetry.instrumentation.genai.openai` and a
`FileSpanExporter` writing `genai/spans.json` (`genai/instrument.py`). The single `chat qwen3:1.7b` span carries ten
`gen_ai.*` attributes, and I compared them with the registry in `model/gen-ai/registry.yaml` of semantic-conventions
v1.41.1.

**What agrees.** All ten emitted keys exist in that registry under the same names, and the registry marks every one of
them `development`, so none is stable. The request side (`operation.name`, `request.model`, `request.temperature`,
`request.max_tokens`), the response side (`response.id`, `response.model`, `response.finish_reasons`) and the token
counts (`usage.input_tokens`, `usage.output_tokens`) are the attributes the spec describes for an inference span. The
library also names the span `chat <model>`, as the spec's span-name pattern asks.

**What does not, or not quite.** The library follows the spec only by omission where I did not ask for something:
`gen_ai.request.top_p`, `seed`, `stop_sequences` and `frequency_penalty` are defined by the spec but absent from the
span because my request set none of them; that is a property of my call, not a defect of the library. Beyond the
spec's attributes the span also carries `openai.response.system_fingerprint`, a vendor key outside the `gen_ai.*`
namespace, and `server.address` and `server.port`, which are general network attributes. Because I pointed the OpenAI
client at Ollama, `gen_ai.provider.name` says `openai`: it describes the client library's protocol, not the model server
that answered, which is what a dashboard grouping by provider would need to know.

**What it means for a dashboard.** Every attribute is `development`, so a name can change in the next release of the
conventions (this registry already moved the provider attribute from `gen_ai.system` to `gen_ai.provider.name`). A
panel or alert built on these keys needs a version pin and a place to change names, and cost or latency by provider is
not trustworthy when an OpenAI-compatible server stands behind the OpenAI client.
