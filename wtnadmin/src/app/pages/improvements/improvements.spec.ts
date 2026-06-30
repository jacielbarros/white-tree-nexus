import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { Improvement, PdcaEntry, Role } from '@app/core/models';
import { ImprovementsPage } from './improvements';

const IMP: Improvement = { id: 'imp-1', code: 'IMP-0001', title: 'Melhorar backup', description: 'd', origin: 'suggestion', source_ref: null, status: 'proposed', target_type: null, target_id: null };
const PDCA: PdcaEntry[] = [
  { occurred_at: '2026-06-30T10:00:00Z', phase: 'check', kind: 'finding', ref_id: 'f-1', label: 'Constatação', detail: 'd' },
  { occurred_at: '2026-06-30T11:00:00Z', phase: 'act', kind: 'improvement', ref_id: 'imp-1', label: 'IMP-0001', detail: 'd' },
];

function apiStub() {
  return {
    get: vi.fn((path: string) => of(path.includes('/pdca') ? PDCA : [IMP])),
    post: vi.fn((_p: string, _b: unknown) => of(IMP)),
    put: vi.fn((_p: string, _b: unknown) => of(IMP)),
  };
}

function setup(role: Role): { fixture: ComponentFixture<ImprovementsPage>; component: ImprovementsPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [ImprovementsPage],
    providers: [MessageService, provideRouter([]), { provide: ApiService, useValue: api }, { provide: AuthStore, useValue: { currentRole: () => role } }],
  });
  const fixture = TestBed.createComponent(ImprovementsPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('ImprovementsPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('lists improvements', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.get).toHaveBeenCalledWith('/improvements');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('IMP-0001');
  });

  it('creates an improvement', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { newTitle: string; newDescription: string; create(e: Event): void };
    c.newTitle = 'Nova';
    c.newDescription = 'd';
    c.create(new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/improvements', expect.objectContaining({ title: 'Nova' }));
  });

  it('loads the PDCA cycle and groups by phase', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { pdcaId: string; loadPdca(e: Event): void; entriesFor(p: 'plan' | 'check' | 'act'): PdcaEntry[] };
    c.pdcaId = 'gap-1';
    c.loadPdca(new Event('submit'));
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('/improvements/pdca?'));
    expect(c.entriesFor('check').length).toBe(1);
    expect(c.entriesFor('act').length).toBe(1);
  });
});
