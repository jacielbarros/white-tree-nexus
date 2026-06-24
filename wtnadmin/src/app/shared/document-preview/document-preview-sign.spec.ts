import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WritableSignal, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import {
  DocumentPreview as Preview,
  PreviewLayout,
  Role,
  SignaturePlacement,
  SignaturePlacementBase,
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
  pdf_page_metrics: [{ page_number: 1, width_points: 842, height_points: 595, rotation: 0 }],
  default_signature_placement: DEFAULT_PLACEMENT,
};

const CONFIRMED_PLACEMENT: SignaturePlacement = {
  ...DEFAULT_PLACEMENT,
  origin: 'user',
  id: 'placement-1',
  preview_id: PREVIEW.id,
  placement_revision: 1,
  placement_hash: 'p'.repeat(64),
  created_by: 'user-1',
  created_at: '2026-06-23T17:05:00Z',
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
  placement_id: CONFIRMED_PLACEMENT.id,
  placement_hash: CONFIRMED_PLACEMENT.placement_hash,
  created_at: '2026-06-23T17:10:00Z',
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
  signature_method: 'internal_electronic_signature',
  visual_signature_present: true,
  signature_placement: SIGNED_PLACEMENT,
};

function apiStub() {
  return {
    createDocumentPreview: vi.fn(() => of(PREVIEW)),
    downloadPreviewPdf: vi.fn(),
    openPreviewInlinePdf: vi.fn(() => of(new Blob(['preview'], { type: 'application/pdf' }))),
    getPreviewLayout: vi.fn(() => of(LAYOUT)),
    confirmSignaturePlacement: vi.fn(() => of(CONFIRMED_PLACEMENT)),
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

    expect(api.signDocumentPreview).toHaveBeenCalledWith('preview-1', PREVIEW.snapshot_hash, null);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('WTN-GAP-0001');

    (component as unknown as { downloadSigned(): void }).downloadSigned();
    expect(api.downloadSignedPdf).toHaveBeenCalledWith('signed-1');
  });

  it('sends the confirmed placement id when the user confirms a visual position', () => {
    const view = component as unknown as {
      generatePreview(): void;
      confirmPlacement(placement: SignaturePlacementBase): void;
      signPreview(): void;
    };

    const userPlacement: SignaturePlacementBase = { ...DEFAULT_PLACEMENT, origin: 'user' };
    view.generatePreview();
    view.confirmPlacement(userPlacement);
    view.signPreview();

    expect(api.confirmSignaturePlacement).toHaveBeenCalledWith('preview-1', userPlacement, PREVIEW.snapshot_hash);
    expect(api.signDocumentPreview).toHaveBeenCalledWith('preview-1', PREVIEW.snapshot_hash, CONFIRMED_PLACEMENT.id);
  });

  it('shows validation feedback when placement confirmation fails', () => {
    const messages = TestBed.inject(MessageService);
    const add = vi.spyOn(messages, 'add');
    api.confirmSignaturePlacement.mockReturnValueOnce(throwError(() => ({ error: { detail: 'Selo fora da pagina' } })));

    (component as unknown as { generatePreview(): void; confirmPlacement(placement: SignaturePlacementBase): void }).generatePreview();
    (component as unknown as { confirmPlacement(placement: SignaturePlacementBase): void }).confirmPlacement({
      ...DEFAULT_PLACEMENT,
      origin: 'user',
    });

    expect(add).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'error',
      summary: 'Posicao invalida',
      detail: 'Selo fora da pagina',
    }));
  });
});
