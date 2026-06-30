import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { EvidenceSummary, Role } from '@app/core/models';
import { EvidenceRepositoryPage } from './evidence-repository';

const EVIDENCE: EvidenceSummary = {
  id: 'ev-1',
  title: 'Política de Backup',
  description: null,
  classification: 'uso_interno',
  status: 'active',
  current_version_id: 'ver-1',
  file_name: 'backup.pdf',
  mime_type: 'application/pdf',
  extension: '.pdf',
  size_bytes: 4096,
  content_hash: 'c'.repeat(64),
  hash_algorithm: 'sha256',
  uploaded_by: 'user-1',
  uploaded_at: '2026-06-30T10:00:00Z',
  created_at: '2026-06-30T10:00:00Z',
  can_download: true,
  links: [{ id: 'lnk-1', target_type: 'risk', target_id: 'risk-1', active: true }],
};

function apiStub() {
  return {
    listEvidence: vi.fn((_params?: Record<string, string>) => of([EVIDENCE])),
    downloadEvidence: vi.fn((_id: string) => of(new Blob(['x'], { type: 'application/pdf' }))),
  };
}

function storeStub(role: Role) {
  return { currentRole: () => role };
}

function setup(role: Role): { fixture: ComponentFixture<EvidenceRepositoryPage>; component: EvidenceRepositoryPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:x') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });

  TestBed.configureTestingModule({
    imports: [EvidenceRepositoryPage],
    providers: [
      MessageService,
      { provide: ApiService, useValue: api },
      { provide: AuthStore, useValue: storeStub(role) },
    ],
  });

  const fixture = TestBed.createComponent(EvidenceRepositoryPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('EvidenceRepositoryPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads the central repository on init', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.listEvidence).toHaveBeenCalledWith({});
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Política de Backup');
    expect(text).toContain('Risco'); // chip do artefato vinculado
  });

  it('sends active filters as query params', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { q: string; targetType: string; classification: string; load(): void };
    c.q = 'backup';
    c.targetType = 'risk';
    c.classification = 'confidencial';
    c.load();
    expect(api.listEvidence).toHaveBeenLastCalledWith({ q: 'backup', target_type: 'risk', classification: 'confidencial' });
  });

  it('exposes the inactive filter only to managers', () => {
    const manager = setup('org_admin');
    expect((manager.fixture.nativeElement as HTMLElement).querySelectorAll('select').length).toBe(3);

    const viewer = setup('client');
    expect((viewer.fixture.nativeElement as HTMLElement).querySelectorAll('select').length).toBe(2);
  });

  it('downloads evidence content', () => {
    const { component, api } = setup('org_admin');
    (component as unknown as { download(ev: EvidenceSummary): void }).download(EVIDENCE);
    expect(api.downloadEvidence).toHaveBeenCalledWith('ev-1');
    expect(URL.createObjectURL).toHaveBeenCalled();
  });
});
