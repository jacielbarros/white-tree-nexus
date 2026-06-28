import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach } from 'vitest';

import { RiskDashboardPage } from './risk-dashboard';
import type { RiskDashboard } from '@app/core/models';

const DASH: RiskDashboard = {
  heatmap: [{ probability: 4, impact: 4, level_key: 'critical', count: 1 }],
  by_level: { low: 1, high: 0, critical: 2 },
  top_risks: ['r1'],
  without_treatment: 3,
  accepted: 1,
  residual_pending: 1,
  by_owner: {},
  by_asset: {},
  inherent_vs_residual: { inherent_above: 2, residual_above: 0 },
};

describe('RiskDashboardPage', () => {
  let component: RiskDashboardPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskDashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    component = TestBed.createComponent(RiskDashboardPage).componentInstance;
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('builds level bars in order, excluding zeros, with labels and colors', () => {
    component.d.set(DASH);
    const bars = component.byLevel();
    expect(bars.map((b) => b.label)).toEqual(['Baixo', 'Crítico']); // high=0 excluded
    expect(bars.find((b) => b.label === 'Crítico')?.color).toBe('#c62828');
    expect(component.cellCount(DASH, 4, 4)).toBe(1);
    expect(component.cellColor(DASH, 4, 4)).toBe('#c62828');
  });
});
