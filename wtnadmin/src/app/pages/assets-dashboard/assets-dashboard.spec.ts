import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach } from 'vitest';

import { AssetsDashboardPage } from './assets-dashboard';
import { AuthStore } from '@app/core/auth.store';

const DASH = {
  by_type: { information_asset: 4, supplier: 1, system: 0 },
  by_criticality: { baixa: 1, media: 0, alta: 2, critica: 2, unset: 1 },
  by_scope: { in_scope: 3, out_of_scope: 1, under_analysis: 2 },
  by_review_status: { up_to_date: 1, due_soon: 0, overdue: 2, undefined: 3 },
  with_personal_data: 2,
  critical_without_review: 1,
  without_responsible: 2,
};

describe('AssetsDashboardPage', () => {
  let component: AssetsDashboardPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetsDashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(AssetsDashboardPage).componentInstance;
  });

  it('should create and start loading', () => {
    expect(component).toBeTruthy();
    expect(component.loading()).toBe(true);
  });

  it('builds bars excluding zero values and translating labels', () => {
    component.dashboard.set(DASH);
    const types = component.byType();
    expect(types.map((b) => b.label)).toEqual(['Ativo de informação', 'Fornecedor/terceiro']);
    expect(types[0].value).toBe(4);
    expect(Math.round(types[0].percent)).toBe(100);
  });

  it('translates criticality and review labels', () => {
    component.dashboard.set(DASH);
    expect(component.byCriticality().map((b) => b.label)).toContain('Crítica');
    expect(component.byReview().map((b) => b.label)).toContain('Vencida');
  });
});
