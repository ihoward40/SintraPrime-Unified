import { describe, expect, it } from 'vitest';
import { chooseGraphicsPreset, GRAPHICS_PRESETS } from './townWorld';
import { createWalkUpProjection } from './walkUpInteraction';

describe('SP-MC3D-001 world governance', () => {
  it('selects lite mode for a GT 1030 class renderer', () => {
    expect(chooseGraphicsPreset({ renderer: 'NVIDIA GeForce GT 1030', deviceMemoryGb: 2 })).toBe('lite');
    expect(GRAPHICS_PRESETS.lite.volumetrics).toBe(false);
    expect(GRAPHICS_PRESETS.lite.reflections).toBe(false);
  });

  it('admits cinematic mode only for RTX-class evidence with sufficient memory', () => {
    expect(chooseGraphicsPreset({ renderer: 'NVIDIA RTX 4080', deviceMemoryGb: 16 })).toBe('cinematic');
    expect(chooseGraphicsPreset({ renderer: 'NVIDIA RTX', deviceMemoryGb: 4 })).not.toBe('cinematic');
  });

  it('walk-up projection cannot execute, approve, or grant authority', () => {
    const projection = createWalkUpProjection({
      interactionId: 'walk-1',
      principalId: 'principal',
      targetDistrict: 'agents',
      intent: 'inspect-district',
      requestedAt: '2026-09-27T00:00:00Z',
    });
    expect(projection.mode).toBe('projection-only');
    expect(projection.canExecute).toBe(false);
    expect(projection.canApprove).toBe(false);
    expect(projection.canGrantAuthority).toBe(false);
  });
});
