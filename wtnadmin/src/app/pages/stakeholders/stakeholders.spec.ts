import { describe, expect, it } from 'vitest';

function derive(power: string, interest: string): string {
  if (power === 'alto' && interest === 'alto') return 'manage_closely';
  if (power === 'alto') return 'keep_satisfied';
  if (interest === 'alto') return 'keep_informed';
  return 'monitor';
}

describe('stakeholder strategy derivation', () => {
  it('covers the Mendelow combinations used by the API', () => {
    expect(derive('alto', 'alto')).toBe('manage_closely');
    expect(derive('alto', 'baixo')).toBe('keep_satisfied');
    expect(derive('medio', 'alto')).toBe('keep_informed');
    expect(derive('baixo', 'baixo')).toBe('monitor');
  });
});
