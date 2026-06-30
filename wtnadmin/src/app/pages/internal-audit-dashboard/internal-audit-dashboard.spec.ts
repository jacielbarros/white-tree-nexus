import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuditDashboardData } from '@app/core/models';
import { InternalAuditDashboardPage } from './internal-audit-dashboard';

const DATA: AuditDashboardData = {
  evidence_by_status: { active: 5, inactive: 1 },
  evidence_by_classification: { confidencial: 3, uso_interno: 2 },
  audits_by_status: { planned: 2, completed: 1 },
  findings_by_type: { nc_maior: 1, conforme: 4 },
};

function apiStub(data: AuditDashboardData | Record<string, never> = DATA) {
  return { get: vi.fn((_path: string) => of(data)) };
}

function setup(data?: AuditDashboardData | Record<string, never>): { fixture: ComponentFixture<InternalAuditDashboardPage>; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub(data ?? DATA);
  TestBed.configureTestingModule({
    imports: [InternalAuditDashboardPage],
    providers: [MessageService, { provide: ApiService, useValue: api }],
  });
  const fixture = TestBed.createComponent(InternalAuditDashboardPage);
  fixture.detectChanges();
  return { fixture, api };
}

describe('InternalAuditDashboardPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads module metrics on init', () => {
    const { fixture, api } = setup();
    expect(api.get).toHaveBeenCalledWith('/internal-audit/dashboard');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Auditorias por status');
    expect(text).toContain('Constatações por tipo');
  });

  it('maps known keys to readable labels', () => {
    const { fixture } = setup();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ativas'); // evidence status
    expect(text).toContain('Confidencial'); // classification
    expect(text).toContain('Concluída'); // audit status
    expect(text).toContain('NC maior'); // finding type
  });

  it('renders empty state per card when dicts are empty', () => {
    const { fixture } = setup({ evidence_by_status: {}, evidence_by_classification: {}, audits_by_status: {}, findings_by_type: {} });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Nenhuma auditoria.');
    expect(text).toContain('Nenhuma constatação.');
  });
});
