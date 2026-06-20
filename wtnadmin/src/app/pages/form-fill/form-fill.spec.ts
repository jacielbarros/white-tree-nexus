import { describe, it, expect } from 'vitest';

import { FormField } from '@app/core/models';
import { groupFields } from './form-fill';

function field(partial: Partial<FormField> & { key: string }): FormField {
  return { label: partial.key, type: 'text', ...partial };
}

describe('groupFields', () => {
  it('retorna lista vazia para entrada vazia', () => {
    expect(groupFields([])).toEqual([]);
  });

  it('campos sem seção ficam num único grupo sem título, ordenados por order', () => {
    const groups = groupFields([
      field({ key: 'b', order: 1 }),
      field({ key: 'a', order: 0 }),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].section).toBe('');
    expect(groups[0].items.map((f) => f.key)).toEqual(['a', 'b']);
  });

  it('order ausente é tratado como 0', () => {
    const groups = groupFields([
      field({ key: 'semOrder' }),
      field({ key: 'comOrder', order: -1 }),
    ]);
    // comOrder (-1) vem antes de semOrder (0)
    expect(groups[0].items.map((f) => f.key)).toEqual(['comOrder', 'semOrder']);
  });

  it('agrupa por seção; a ordem das seções segue a 1ª aparição após ordenar por order', () => {
    const groups = groupFields([
      field({ key: 'x2', section: 'X', order: 2 }),
      field({ key: 'y1', section: 'Y', order: 1 }),
      field({ key: 'x0', section: 'X', order: 0 }),
    ]);
    // sorted por order: x0(0), y1(1), x2(2) → 1ª seção é X (no order 0), depois Y
    expect(groups.map((g) => g.section)).toEqual(['X', 'Y']);
    expect(groups[0].items.map((f) => f.key)).toEqual(['x0', 'x2']); // dentro de X, por order
    expect(groups[1].items.map((f) => f.key)).toEqual(['y1']);
  });

  it('faz trim da seção e une seções equivalentes', () => {
    const groups = groupFields([
      field({ key: 'a', section: '  Dados  ', order: 0 }),
      field({ key: 'b', section: 'Dados', order: 1 }),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].section).toBe('Dados');
    expect(groups[0].items.map((f) => f.key)).toEqual(['a', 'b']);
  });

  it('não muta o array de entrada', () => {
    const input = [field({ key: 'b', order: 1 }), field({ key: 'a', order: 0 })];
    const snapshot = input.map((f) => f.key);
    groupFields(input);
    expect(input.map((f) => f.key)).toEqual(snapshot);
  });
});
