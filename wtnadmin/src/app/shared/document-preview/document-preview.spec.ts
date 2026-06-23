import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { DocumentPreview as Preview, SignedDocument } from '@app/core/models';
import { DocumentPreview } from './document-preview';

const PREVIEW: Preview = {
  id: 'preview-1',
  document_type: 'context_report',
  source_artifact_id: null,
  template_version_id: 'template-version-1',
  classification: 'uso_interno',
  status: 'active',
  snapshot_hash: 'a'.repeat(64),
  preview_pdf_hash: 'b'.repeat(64),
  expires_at: '2026-06-23T18:00:00Z',
  created_at: '2026-06-23T17:00:00Z',
  warnings: [],
};

const SIGNED: SignedDocument = {
  id: 'signed-1',
  document_type: 'context_report',
  source_artifact_id: null,
  template_version_id: 'template-version-1',
  version_number: 1,
  status: 'signed',
  classification: 'uso_interno',
  identifier: 'WTN-CONTEXT-0001',
  pdf_hash: 'c'.repeat(64),
  snapshot_hash: PREVIEW.snapshot_hash,
  size_bytes: 1200,
  signed_by: 'user-1',
  signed_at: '2026-06-23T17:10:00Z',
};

function apiStub() {
  return {
    createDocumentPreview: vi.fn(() => of(PREVIEW)),
    downloadPreviewPdf: vi.fn(() => of(new Blob(['preview'], { type: 'application/pdf' }))),
    signDocumentPreview: vi.fn(() => of(SIGNED)),
    downloadSignedPdf: vi.fn(() => of(new Blob(['signed'], { type: 'application/pdf' }))),
  };
}

describe('DocumentPreview', () => {
  let fixture: ComponentFixture<DocumentPreview>;
  let component: DocumentPreview;
  let api: ReturnType<typeof apiStub>;

  beforeEach(async () => {
    api = apiStub();
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:pdf') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });

    await TestBed.configureTestingModule({
      imports: [DocumentPreview],
      providers: [
        MessageService,
        { provide: ApiService, useValue: api },
        { provide: AuthStore, useValue: { currentRole: vi.fn(() => 'org_admin') } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentPreview);
    fixture.componentRef.setInput('documentType', 'context_report');
    fixture.componentRef.setInput('title', 'Contexto');
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders empty state before preview generation', () => {
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nenhum preview gerado');
  });

  it('generates a preview with classification and source artifact', () => {
    fixture.componentRef.setInput('sourceArtifactId', 'context-1');
    (component as unknown as { generatePreview(): void }).generatePreview();
    fixture.detectChanges();

    expect(api.createDocumentPreview).toHaveBeenCalledWith({
      document_type: 'context_report',
      source_artifact_id: 'context-1',
      classification: 'uso_interno',
    });
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Preview ativo');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Template template');
  });

  it('downloads the preliminary PDF from the generated preview', () => {
    (component as unknown as { generatePreview(): void; downloadPreview(): void }).generatePreview();
    (component as unknown as { downloadPreview(): void }).downloadPreview();

    expect(api.downloadPreviewPdf).toHaveBeenCalledWith('preview-1');
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it('shows an actionable error when preview generation fails', () => {
    const messages = TestBed.inject(MessageService);
    const add = vi.spyOn(messages, 'add');
    api.createDocumentPreview.mockReturnValue(throwError(() => ({ error: { detail: 'Dados insuficientes' } })));

    (component as unknown as { generatePreview(): void }).generatePreview();

    expect(add).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'error',
      summary: 'Erro ao gerar preview',
      detail: 'Dados insuficientes',
    }));
  });
});
