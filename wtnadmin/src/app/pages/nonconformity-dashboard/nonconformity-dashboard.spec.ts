import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { NcDashboard } from '@app/core/models';
import { NonconformityDashboardPage } from './nonconformity-dashboard';

const DASH: NcDashboard = {
  nc_by_status: { open: 2, closed: 1 },
  nc_by_severity: { maior: 1, menor: 2 },
  overdue_actions: 3,
  improvements_by_status: { proposed: 1 },
};

function apiStub() {
  return { get: vi.fn((_p: string) => of(DASH)) };
}

function setup(): { fixture: ComponentFixture<NonconformityDashboardPage>; component: NonconformityDashboardPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [NonconformityDashboardPage],
    providers: [MessageService, provideRouter([]), { provide: ApiService, useValue: api }],
  });
  const fixture = TestBed.createComponent(NonconformityDashboardPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('NonconformityDashboardPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads metrics and renders KPIs', () => {
    const { fixture, api } = setup();
    expect(api.get).toHaveBeenCalledWith('/nonconformities/dashboard');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ações vencidas');
    expect(text).toContain('3'); // overdue_actions KPI
  });

  it('totals a record', () => {
    const { component } = setup();
    const c = component as unknown as { total(r: Record<string, number>): number };
    expect(c.total({ open: 2, closed: 1 })).toBe(3);
  });
});
