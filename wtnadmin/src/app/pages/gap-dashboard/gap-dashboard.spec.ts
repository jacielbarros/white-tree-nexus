import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapDashboardPage } from './gap-dashboard';
import { AuthStore } from '@app/core/auth.store';

const DASH = {
  consolidated_conformance: 0.3,
  total_items: 10,
  evaluated_items: 4,
  dimensions: {
    clause: { conformance: 0.5, adherence_evaluated: 1, evaluated: 2, total: 4 },
    annex_a: { conformance: 0.17, adherence_evaluated: 0.33, evaluated: 2, total: 6 },
  },
  overall_adherence: 0.5,
  completeness: 0.4,
  status_distribution: { meets: 2, partial: 1, not_meet: 1, not_applicable: 0, not_filled: 6 },
  by_dimension: { clause: 0.8, annex_a: 0.4 },
  by_theme: {},
};

describe('GapDashboardPage', () => {
  let component: GapDashboardPage;
  // acesso a membros protegidos (computeds/helpers da UI) nos testes
  let view: {
    totalControls(): number;
    scoredControls(): number;
    evaluatedControls(): number;
    completenessPercentLabel(): string;
    conservativeAdherenceRatio(): number | null;
    conservativePercentLabel(): string;
    statusViews(): { key: string; count: number; percent: number }[];
    dimensionViews(): { key: string; value: number | null }[];
    percentLabel(v: number | null): string;
    statusTagClass(s: string): string;
    consolidatedPercentLabel(): string;
    dimLabel(key: string): string;
    overallPercentLabel(): string;
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GapDashboardPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
      ],
    }).compileComponents();

    const store = TestBed.inject(AuthStore);
    store.setToken('fake-token');

    const fixture = TestBed.createComponent(GapDashboardPage);
    component = fixture.componentInstance;
    view = component as unknown as typeof view;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start loading and with a null dashboard', () => {
    expect(component.loading()).toBe(true);
    expect(component.dashboard()).toBeNull();
  });

  it('counts total and evaluated controls from the distribution', () => {
    component.dashboard.set(DASH as never);
    expect(view.totalControls()).toBe(10);
    expect(view.evaluatedControls()).toBe(4); // 10 - 6 não avaliados
    expect(view.scoredControls()).toBe(4); // meets + partial + not_meet
    expect(view.completenessPercentLabel()).toBe('40%');
  });

  it('calculates conservative adherence with not evaluated as zero evidence', () => {
    component.dashboard.set(DASH as never);

    expect(view.conservativeAdherenceRatio()).toBe(0.25);
    expect(view.conservativePercentLabel()).toBe('25%');
  });

  it('excludes N/A but includes not evaluated in conservative adherence denominator', () => {
    component.dashboard.set({
      ...DASH,
      status_distribution: { meets: 1, partial: 1, not_meet: 1, not_applicable: 1, not_filled: 96 },
    } as never);

    expect(view.evaluatedControls()).toBe(4);
    expect(view.scoredControls()).toBe(3);
    expect(view.conservativePercentLabel()).toBe('2%');
  });

  it('builds status views with counts and percentages', () => {
    component.dashboard.set(DASH as never);
    const meets = view.statusViews().find((s) => s.key === 'meets')!;
    expect(meets.count).toBe(2);
    expect(Math.round(meets.percent)).toBe(20);
  });

  it('builds dimension views (falls back to by_dimension when by_theme is empty)', () => {
    component.dashboard.set(DASH as never);
    const keys = view.dimensionViews().map((d) => d.key);
    expect(keys).toEqual(['clause', 'annex_a']);
  });

  it('percentLabel formats ratio and dash', () => {
    expect(view.percentLabel(0.5)).toBe('50%');
    expect(view.percentLabel(null)).toBe('—');
  });

  it('statusTagClass maps to wtn-tag modifiers', () => {
    expect(view.statusTagClass('meets')).toBe('wtn-tag--success');
    expect(view.statusTagClass('not_meet')).toBe('wtn-tag--danger');
  });

  it('leads with consolidated conformance, not adherence of evaluated', () => {
    component.dashboard.set(DASH as never);
    expect(view.consolidatedPercentLabel()).toBe('30%');
    expect(view.overallPercentLabel()).toBe('50%');
  });

  it('decomposes conformance by dimension with coverage', () => {
    component.dashboard.set(DASH as never);
    expect(view.dimLabel('clause')).toBe('50% · 2/4');
    expect(view.dimLabel('annex_a')).toBe('17% · 2/6');
    expect(view.dimLabel('missing')).toBe('—');
  });
});
