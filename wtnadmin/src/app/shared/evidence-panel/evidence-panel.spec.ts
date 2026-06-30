import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { EvidenceSummary } from '@app/core/models';
import { EvidencePanel } from './evidence-panel';

const EVIDENCE: EvidenceSummary = {
  id: 'ev-1',
  title: 'Política de Acesso',
  description: null,
  classification: 'confidencial',
  status: 'active',
  current_version_id: 'ver-1',
  file_name: 'policy.pdf',
  mime_type: 'application/pdf',
  extension: '.pdf',
  size_bytes: 2048,
  content_hash: 'a'.repeat(64),
  hash_algorithm: 'sha256',
  uploaded_by: 'user-1',
  uploaded_at: '2026-06-30T12:00:00Z',
  created_at: '2026-06-30T12:00:00Z',
  can_download: false,
  links: [{ id: 'lnk-1', target_type: 'soa_item', target_id: 'soa-item-1', active: true }],
};

function apiStub() {
  return {
    listEvidence: vi.fn((_params?: Record<string, string>) => of([EVIDENCE])),
    uploadEvidence: vi.fn((_form: FormData) => of(EVIDENCE)),
    downloadEvidence: vi.fn((_id: string) => of(new Blob(['x'], { type: 'application/pdf' }))),
    inactivateEvidence: vi.fn((_id: string) => of(void 0)),
  };
}

function setup(canManage: boolean): { fixture: ComponentFixture<EvidencePanel>; component: EvidencePanel; api: ReturnType<typeof apiStub> } {
  const api = apiStub();
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:x') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });

  TestBed.configureTestingModule({
    imports: [EvidencePanel],
    providers: [MessageService, { provide: ApiService, useValue: api }],
  });

  const fixture = TestBed.createComponent(EvidencePanel);
  fixture.componentRef.setInput('targetType', 'soa_item');
  fixture.componentRef.setInput('targetId', 'soa-item-1');
  fixture.componentRef.setInput('canManage', canManage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('EvidencePanel', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads evidence scoped to the target artifact', () => {
    const { fixture, api } = setup(true);
    expect(api.listEvidence).toHaveBeenCalledWith({ target_type: 'soa_item', target_id: 'soa-item-1' });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Política de Acesso');
    expect(text).toContain('Confidencial');
  });

  it('hides the upload form when the user cannot manage', () => {
    const { fixture } = setup(false);
    expect((fixture.nativeElement as HTMLElement).querySelector('.ev__upload')).toBeNull();
  });

  it('shows the upload form when the user can manage', () => {
    const { fixture } = setup(true);
    expect((fixture.nativeElement as HTMLElement).querySelector('.ev__upload')).not.toBeNull();
  });

  it('uploads a selected file as multipart with target metadata', () => {
    const { component, api } = setup(true);
    const c = component as unknown as {
      selectedFile: { set(f: File | null): void };
      classification: string;
      upload(e: Event): void;
    };
    c.selectedFile.set(new File(['data'], 'doc.pdf', { type: 'application/pdf' }));
    c.classification = 'uso_interno';
    c.upload(new Event('submit'));

    expect(api.uploadEvidence).toHaveBeenCalledTimes(1);
    const form = api.uploadEvidence.mock.calls[0][0] as FormData;
    expect(form.get('target_type')).toBe('soa_item');
    expect(form.get('target_id')).toBe('soa-item-1');
    expect(form.get('classification')).toBe('uso_interno');
  });

  it('inactivates an evidence and reloads', () => {
    const { component, api } = setup(true);
    (component as unknown as { inactivate(ev: EvidenceSummary): void }).inactivate(EVIDENCE);
    expect(api.inactivateEvidence).toHaveBeenCalledWith('ev-1');
    expect(api.listEvidence).toHaveBeenCalledTimes(2); // load inicial + reload
  });
});
