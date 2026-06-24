import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import {
  DocumentPreview as Preview,
  PreviewLayout,
  SignaturePlacement,
  SignedDocument,
  SignedSignaturePlacement,
} from '@app/core/models';
import { DocumentPreview } from './document-preview';

const DEFAULT_PLACEMENT = {
  page_number: 1,
  x_points: 626,
  y_points: 36,
  width_points: 180,
  height_points: 54,
  page_width_points: 842,
  page_height_points: 595,
  coordinate_system: 'pdf_points_bottom_left' as const,
  origin: 'default' as const,
};

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
  pdf_page_metrics: [{ page_number: 1, width_points: 842, height_points: 595, rotation: 0 }],
  default_signature_placement: DEFAULT_PLACEMENT,
};

const LAYOUT: PreviewLayout = {
  preview_id: PREVIEW.id,
  document_type: PREVIEW.document_type,
  snapshot_hash: PREVIEW.snapshot_hash,
  page_metrics: PREVIEW.pdf_page_metrics,
  blocked_areas: [],
  default_placement: DEFAULT_PLACEMENT,
  latest_placement: null,
};

const SIGNED_PLACEMENT: SignedSignaturePlacement = {
  ...DEFAULT_PLACEMENT,
  id: 'signed-placement-1',
  signed_document_id: 'signed-1',
  placement_id: 'placement-1',
  placement_hash: 'p'.repeat(64),
  created_at: '2026-06-23T17:10:00Z',
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
  signature_method: 'internal_electronic_signature',
  visual_signature_present: true,
  signature_placement: SIGNED_PLACEMENT,
};

function apiStub() {
  return {
    createDocumentPreview: vi.fn(() => of(PREVIEW)),
    downloadPreviewPdf: vi.fn(() => of(new Blob(['preview'], { type: 'application/pdf' }))),
    openPreviewInlinePdf: vi.fn(() => of(new Blob(['preview'], { type: 'application/pdf' }))),
    getPreviewLayout: vi.fn(() => of(LAYOUT)),
    confirmSignaturePlacement: vi.fn((_previewId: string, placement: typeof DEFAULT_PLACEMENT) => of({
      ...placement,
      id: 'placement-1',
      preview_id: PREVIEW.id,
      placement_revision: 1,
      placement_hash: 'p'.repeat(64),
      created_by: 'user-1',
      created_at: '2026-06-23T17:05:00Z',
    } satisfies SignaturePlacement)),
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
    expect(api.openPreviewInlinePdf).toHaveBeenCalledWith('preview-1');
    expect(api.getPreviewLayout).toHaveBeenCalledWith('preview-1');
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
