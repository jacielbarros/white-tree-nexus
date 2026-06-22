import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { DashboardPage } from './dashboard';

const DASHBOARD = {
  organization_id: 't1',
  organization_name: 'Org',
  kpis: {
    overall_adherence: 0.62,
    controls_evaluated: 30,
    controls_total: 93,
    critical_gaps: 5,
    modules_approved: 1,
    modules_total: 3,
  },
  cards: [
    {
      id: 'context',
      title: 'Contexto · Cláusula 4',
      status: 'in_force',
      progress_pct: 100,
      responsible: null,
      deadline: null,
      overdue: false,
      next_action: { label: 'Ver visão consolidada', route: 'context-overview', fragment: null },
      not_started: false,
      placeholder: false,
    },
    {
      id: 'gap',
      title: 'Gap Analysis · Anexo A',
      status: 'draft',
      progress_pct: 32,
      responsible: 'Ana',
      deadline: '2026-08-01',
      overdue: false,
      next_action: { label: 'Avaliar controles', route: 'gap-analysis', fragment: null },
      not_started: false,
      placeholder: false,
    },
    {
      id: 'soa',
      title: 'Declaração de Aplicabilidade',
      status: 'not_started',
      progress_pct: null,
      responsible: null,
      deadline: null,
      overdue: false,
      next_action: { label: 'Consolidar do Gap', route: 'soa', fragment: null },
      not_started: true,
      placeholder: false,
    },
    {
      id: 'action_plan',
      title: 'Plano de Ação',
      status: 'not_started',
      progress_pct: null,
      responsible: null,
      deadline: null,
      overdue: false,
      next_action: { label: 'Em breve · Módulo 4', route: 'dashboard', fragment: null },
      not_started: true,
      placeholder: true,
    },
  ],
  adherence_trend: [
    { date: '2026-01-01', adherence: 0.45, version: 1 },
    { date: '2026-04-01', adherence: 0.62, version: 2 },
  ],
  generated_at: '2026-06-21T00:00:00Z',
};

const mockApi = { get: vi.fn(() => of(DASHBOARD)) };
const mockStore = {
  me: vi.fn(() => ({ email: 'a@b.com', memberships: [{ tenant_id: 't1', org_name: 'Org' }] })),
  activeOrgId: vi.fn(() => 't1'),
};

describe('DashboardPage', () => {
  beforeEach(async () => {
    mockApi.get.mockClear();
    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: mockApi },
        { provide: AuthStore, useValue: mockStore },
      ],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('calls the single /dashboard endpoint', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    expect(mockApi.get).toHaveBeenCalledWith('/dashboard');
  });

  it('renders overall adherence KPI', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('62%');
  });

  it('renders 3 non-placeholder module cards', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    const cards = fixture.nativeElement.querySelectorAll('.wtn-module-card:not(.wtn-module-card--future)');
    expect(cards.length).toBe(3);
  });

  it('renders the placeholder card as future', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    const future = fixture.nativeElement.querySelectorAll('.wtn-module-card--future');
    expect(future.length).toBe(1);
  });

  it('shows org name and critical gap count', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Org');
    expect(fixture.nativeElement.textContent).toContain('5');
  });

  it('renders the adherence sparkline when trend present', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.wtn-sparkline')).toBeTruthy();
  });
});
