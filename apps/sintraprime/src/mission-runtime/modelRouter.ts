import type { MissionSpec, MissionState, ModelAdapter, ModelProposal } from './types.js';

export class ModelRouter {
  private readonly adapters = new Map<string, ModelAdapter>();

  register(adapter: ModelAdapter): void {
    if (this.adapters.has(adapter.id)) {
      throw new Error(`Model adapter already registered: ${adapter.id}`);
    }
    this.adapters.set(adapter.id, adapter);
  }

  get(id: string): ModelAdapter | undefined {
    return this.adapters.get(id);
  }

  list(): string[] {
    return [...this.adapters.keys()];
  }

  async collect(spec: MissionSpec, state: MissionState, context?: unknown): Promise<ModelProposal[]> {
    const selected = spec.allowedModels.map((id) => {
      const adapter = this.adapters.get(id);
      if (!adapter) throw new Error(`Authorized model adapter is not registered: ${id}`);
      return adapter;
    });

    return Promise.all(selected.map((adapter) => adapter.propose(spec, state, context)));
  }

  select(proposals: ModelProposal[]): ModelProposal | undefined {
    const actionable = proposals.filter((p) => p.action && !p.stop);
    actionable.sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));
    return actionable[0] ?? proposals.find((p) => p.stop);
  }
}
