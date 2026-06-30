import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { AuditProgram, AuditSummary, MembershipRow, Role } from '@app/core/models';
import { InternalAuditPage } from './internal-audit';

const PROGRAM: AuditProgram = { id: 'prog-1', name: 'Programa 2026', objective: null, period_start: null, period_end: null, created_at: '2026-06-30T10:00:00Z' };
const AUDIT: AuditSummary = { id: 'aud-1', program_id: 'prog-1', code: 'AUD-0001', title: 'Auditoria A.5', status: 'in_progress', auditor_member_id: 'user-1', period_start: null, period_end: null, current_version_id: null, draft_status: 'draft' };
const MEMBER: MembershipRow = { id: 'm-1', user_id: 'user-1', email: 'a@x.com', full_name: 'Auditor', role: 'org_admin', status: 'active', locked: false };

function apiStub() {
  return {
    get: vi.fn((path: string) => of(path.includes('programs') ? [PROGRAM] : [AUDIT])),
    listUsers: vi.fn(() => of([MEMBER])),
    post: vi.fn((_path: string, _body: unknown) => of({})),
  };
}

function setup(role: Role): { fixture: ComponentFixture<InternalAuditPage>; component: InternalAuditPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [InternalAuditPage],
    providers: [MessageService, provideRouter([]), { provide: ApiService, useValue: api }, { provide: AuthStore, useValue: { currentRole: () => role } }],
  });
  const fixture = TestBed.createComponent(InternalAuditPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('InternalAuditPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads programs and audits', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.get).toHaveBeenCalledWith('/internal-audit/programs');
    expect(api.get).toHaveBeenCalledWith('/internal-audit/audits');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('AUD-0001');
    expect(text).toContain('Em andamento'); // status label
  });

  it('creates a program', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { newProgramName: string; createProgram(e: Event): void };
    c.newProgramName = 'Novo';
    c.createProgram(new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/internal-audit/programs', expect.objectContaining({ name: 'Novo' }));
  });

  it('requires all audit fields before enabling creation', () => {
    const { component } = setup('org_admin');
    const c = component as unknown as { canCreateAudit(): boolean; newProgramId: string; newTitle: string; newAuditor: string; newScope: string; newCriteria: string };
    expect(c.canCreateAudit()).toBe(false);
    c.newProgramId = 'prog-1'; c.newTitle = 'T'; c.newAuditor = 'user-1'; c.newScope = 'S'; c.newCriteria = 'C';
    expect(c.canCreateAudit()).toBe(true);
  });

  it('hides creation forms for non-managers', () => {
    const { fixture } = setup('client');
    expect((fixture.nativeElement as HTMLElement).querySelector('.inline-form')).toBeNull();
  });
});
