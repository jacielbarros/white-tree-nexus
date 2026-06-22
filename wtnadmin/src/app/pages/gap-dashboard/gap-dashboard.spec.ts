import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapDashboardPage } from './gap-dashboard';
import { AuthStore } from '@app/core/auth.store';

const DASH = {
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
    evaluatedControls(): number;
    statusViews(): { key: string; count: number; percent: number }[];
    dimensionViews(): { key: string; value: number | null }[];
    percentLabel(v: number | null): string;
    statusTagClass(s: string): string;
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
});
