import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { AuditDetail, AuditFinding, Role } from '@app/core/models';
import { InternalAuditDetailPage } from './internal-audit-detail';

const DETAIL: AuditDetail = {
  id: 'aud-1', program_id: 'prog-1', code: 'AUD-0001', title: 'Auditoria A.5', status: 'in_progress',
  auditor_member_id: 'user-1', period_start: null, period_end: null, current_version_id: null, draft_status: 'draft',
  scope: 'Controles A.5', criteria: 'ISO 27001',
  readiness: { can_approve_report: false, pending_items: 1, findings_count: 1 },
};
const FINDING: AuditFinding = {
  id: 'f-1', audit_id: 'aud-1', finding_type: 'nc_menor', title: 'NC', description: 'desvio',
  checklist_item_id: null, target_type: null, target_id: null, promotable: true, nonconformity_ref: null,
  status: 'active', evidence_links: [],
};

function apiStub() {
  return {
    get: vi.fn((path: string) => {
      if (path.endsWith('/findings')) return of([FINDING]);
      if (path.endsWith('/checklist')) return of([]);
      if (path.endsWith('/versions')) return of([]);
      if (path.includes('/evidence')) return of([]);
      return of(DETAIL);
    }),
    listEvidence: vi.fn(() => of([])),
    post: vi.fn((_p: string, _b: unknown) => of({})),
    put: vi.fn((_p: string, _b: unknown) => of({})),
    delete: vi.fn((_p: string) => of(void 0)),
    getBlob: vi.fn((_p: string) => of(new Blob(['%PDF'], { type: 'application/pdf' }))),
  };
}

function setup(role: Role): { fixture: ComponentFixture<InternalAuditDetailPage>; component: InternalAuditDetailPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [InternalAuditDetailPage],
    providers: [
      MessageService,
      provideRouter([]),
      { provide: ApiService, useValue: api },
      { provide: AuthStore, useValue: { currentRole: () => role } },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'aud-1' } } } },
    ],
  });
  const fixture = TestBed.createComponent(InternalAuditDetailPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('InternalAuditDetailPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads the audit detail with checklist, findings and versions', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.get).toHaveBeenCalledWith('/internal-audit/audits/aud-1');
    expect(api.get).toHaveBeenCalledWith('/internal-audit/audits/aud-1/findings');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('AUD-0001');
    expect(text).toContain('NC menor'); // finding type label
    expect(text).toContain('promovível');
  });

  it('registers a finding via POST', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { newFindingTitle: string; newFindingDesc: string; addFinding(e: Event): void };
    c.newFindingTitle = 'Achado';
    c.newFindingDesc = 'Descrição';
    c.addFinding(new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/internal-audit/audits/aud-1/findings', expect.objectContaining({ finding_type: 'observacao', title: 'Achado' }));
  });

  it('transitions the audit state', () => {
    const { component, api } = setup('org_admin');
    (component as unknown as { transition(a: string): void }).transition('complete');
    expect(api.post).toHaveBeenCalledWith('/internal-audit/audits/aud-1/transition', { action: 'complete' });
  });

  it('approves the report with optional signature', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { signReport: boolean; approve(): void };
    c.signReport = true;
    c.approve();
    expect(api.post).toHaveBeenCalledWith('/internal-audit/audits/aud-1/report/approve', { sign: true, classification: 'uso_interno' });
  });

  it('maps finding and result labels', () => {
    const { component } = setup('org_admin');
    const c = component as unknown as { findingLabel(t: string): string; resultLabel(r: string): string };
    expect(c.findingLabel('nc_maior')).toBe('NC maior');
    expect(c.resultLabel('pendente')).toBe('Pendente');
  });
});
