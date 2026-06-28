import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach } from 'vitest';

import { RisksPage } from './risks';
import { AuthStore } from '@app/core/auth.store';
import type { Risk } from '@app/core/models';

function risk(partial: Partial<Risk>): Risk {
  return {
    id: 'r', code: 'RSK-0001', title: 'T', description: 'd', threat_id: 't', vulnerability_id: 'v',
    asset_item_ids: [], probability_level: 3, impact_level: 4, impact_derived_level: 4,
    impact_is_override: false, inherent_level_key: 'high', above_acceptance: true, owner_user_id: null,
    status: 'assessed', treatment_option: null, residual_probability_level: null, residual_impact_level: null,
    residual_level_key: null, residual_above_acceptance: null, is_archived: false, ...partial,
  };
}

describe('RisksPage', () => {
  let component: RisksPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RisksPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(RisksPage).componentInstance;
  });

  it('creates and starts loading', () => {
    expect(component).toBeTruthy();
    expect(component.loading()).toBe(true);
  });

  it('filters by search, level and above-criterion', () => {
    component.risks.set([
      risk({ id: '1', title: 'Vazamento', inherent_level_key: 'high', above_acceptance: true }),
      risk({ id: '2', title: 'Indisponibilidade', inherent_level_key: 'low', above_acceptance: false }),
    ]);
    component.search.set('vaza');
    expect(component.filtered().map((r) => r.id)).toEqual(['1']);
    component.search.set('');
    component.levelFilter.set('low');
    expect(component.filtered().map((r) => r.id)).toEqual(['2']);
    component.levelFilter.set('');
    component.onlyAbove.set(true);
    expect(component.filtered().map((r) => r.id)).toEqual(['1']);
  });

  it('computes heatmap cell count and labels', () => {
    component.heatmap.set([{ probability: 3, impact: 4, level_key: 'high', count: 2 }]);
    expect(component.cellCount(3, 4)).toBe(2);
    expect(component.cellCount(1, 1)).toBe(0);
    expect(component.level('high')).toBe('Alto');
    expect(component.statusLabel('assessed')).toBe('Avaliado');
  });
});
