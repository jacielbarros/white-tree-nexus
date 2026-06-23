import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WritableSignal, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { DocumentPreview as Preview, Role, SignedDocument } from '@app/core/models';
import { DocumentPreview } from './document-preview';

const PREVIEW: Preview = {
  id: 'preview-1',
  document_type: 'gap_report',
  source_artifact_id: 'gap-1',
  template_version_id: 'template-version-1',
  classification: 'uso_interno',
  status: 'active',
  snapshot_hash: 'd'.repeat(64),
  preview_pdf_hash: 'e'.repeat(64),
  expires_at: '2026-06-23T18:00:00Z',
  created_at: '2026-06-23T17:00:00Z',
  warnings: [],
};

const SIGNED: SignedDocument = {
  id: 'signed-1',
  document_type: 'gap_report',
  source_artifact_id: 'gap-1',
  template_version_id: 'template-version-1',
  version_number: 1,
  status: 'signed',
  classification: 'uso_interno',
  identifier: 'WTN-GAP-0001',
  pdf_hash: 'f'.repeat(64),
  snapshot_hash: PREVIEW.snapshot_hash,
  size_bytes: 2048,
  signed_by: 'user-1',
  signed_at: '2026-06-23T17:10:00Z',
};

function apiStub() {
  return {
    createDocumentPreview: vi.fn(() => of(PREVIEW)),
    downloadPreviewPdf: vi.fn(),
    signDocumentPreview: vi.fn(() => of(SIGNED)),
    downloadSignedPdf: vi.fn(() => of(new Blob(['signed'], { type: 'application/pdf' }))),
  };
}

describe('DocumentPreview signing', () => {
  let fixture: ComponentFixture<DocumentPreview>;
  let component: DocumentPreview;
  let api: ReturnType<typeof apiStub>;
  let currentRole: WritableSignal<Role>;

  beforeEach(async () => {
    api = apiStub();
    currentRole = signal<Role>('org_admin');
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:pdf') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });

    await TestBed.configureTestingModule({
      imports: [DocumentPreview],
      providers: [
        MessageService,
        { provide: ApiService, useValue: api },
        { provide: AuthStore, useValue: { currentRole } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentPreview);
    fixture.componentRef.setInput('documentType', 'gap_report');
    fixture.componentRef.setInput('sourceArtifactId', 'gap-1');
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('enables signing for users with the document approval permission', () => {
    expect((component as unknown as { canSign(): boolean }).canSign()).toBe(true);
  });

  it('hides signing for users without approval permission', () => {
    currentRole.set('client');
    fixture.detectChanges();

    expect((component as unknown as { canSign(): boolean }).canSign()).toBe(false);
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Assinar');
  });

  it('signs the active preview with the confirmed snapshot hash and exposes final download', () => {
    (component as unknown as { generatePreview(): void; signPreview(): void }).generatePreview();
    (component as unknown as { signPreview(): void }).signPreview();
    fixture.detectChanges();

    expect(api.signDocumentPreview).toHaveBeenCalledWith('preview-1', PREVIEW.snapshot_hash);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('WTN-GAP-0001');

    (component as unknown as { downloadSigned(): void }).downloadSigned();
    expect(api.downloadSignedPdf).toHaveBeenCalledWith('signed-1');
  });
});
