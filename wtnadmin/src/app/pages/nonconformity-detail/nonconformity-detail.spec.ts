import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { NCDetail, Role } from '@app/core/models';
import { NonconformityDetailPage } from './nonconformity-detail';

const DETAIL: NCDetail = {
  id: 'nc-1', code: 'NC-0001', origin: 'incident', title: 'Falha', severity: 'maior', status: 'in_verification',
  source_finding_id: null, target_type: null, target_id: null, description: 'desvio', root_cause: null,
  root_cause_method: null,
  readiness: { can_close: false, has_effective_verification: false, overdue_actions: 0, open_actions: 1 },
};

function apiStub() {
  return {
    get: vi.fn((path: string) => {
      if (path.includes('/actions')) return of([]);
      if (path.includes('/verifications')) return of([]);
      return of(DETAIL);
    }),
    post: vi.fn((_p: string, _b: unknown) => of({})),
    put: vi.fn((_p: string, _b: unknown) => of({})),
    listUsers: vi.fn(() => of([])),
    listEvidence: vi.fn(() => of([])),
    listTimeline: vi.fn(() => of([])),
  };
}

function setup(role: Role): { fixture: ComponentFixture<NonconformityDetailPage>; component: NonconformityDetailPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [NonconformityDetailPage],
    providers: [
      MessageService,
      provideRouter([]),
      { provide: ApiService, useValue: api },
      { provide: AuthStore, useValue: { currentRole: () => role } },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'nc-1' } } } },
    ],
  });
  const fixture = TestBed.createComponent(NonconformityDetailPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('NonconformityDetailPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads the NC detail with readiness gate', () => {
    const { fixture } = setup('org_admin');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('NC-0001');
    expect(text).toContain('Em verificação');
  });

  it('disables Encerrar when can_close is false', () => {
    const { fixture } = setup('org_admin');
    const closeBtn = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find((b) => b.textContent?.includes('Encerrar')) as HTMLButtonElement | undefined;
    expect(closeBtn?.disabled).toBe(true);
  });

  it('posts a transition', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { transition(n: NCDetail, a: string): void };
    c.transition(DETAIL, 'send-verify');
    expect(api.post).toHaveBeenCalledWith('/nonconformities/nc-1/transition', { action: 'send-verify' });
  });

  it('registers a verification', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { verResult: string; addVerification(n: NCDetail, e: Event): void };
    c.addVerification(DETAIL, new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/nonconformities/nc-1/verifications', expect.objectContaining({ result: 'effective' }));
  });
});
