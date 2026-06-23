import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { IntegrityVerification, SignedDocument } from '@app/core/models';
import { DocumentHistory } from './document-history';

const SIGNED: SignedDocument = {
  id: 'signed-1',
  document_type: 'soa_report',
  source_artifact_id: 'soa-1',
  template_version_id: 'template-version-1',
  version_number: 2,
  status: 'obsolete',
  classification: 'uso_interno',
  identifier: 'WTN-SOA-0002',
  pdf_hash: 'a'.repeat(64),
  snapshot_hash: 'b'.repeat(64),
  size_bytes: 4096,
  signed_by: 'user-1',
  signed_at: '2026-06-23T17:10:00Z',
};

const VERIFY: IntegrityVerification = {
  valid: true,
  identifier: SIGNED.identifier,
  pdf_hash: SIGNED.pdf_hash,
  snapshot_hash: SIGNED.snapshot_hash,
  verified_at: '2026-06-23T17:20:00Z',
};

function apiStub() {
  return {
    listSignedDocuments: vi.fn(() => of([SIGNED])),
    downloadSignedPdf: vi.fn(() => of(new Blob(['signed'], { type: 'application/pdf' }))),
    verifySignedDocument: vi.fn(() => of(VERIFY)),
  };
}

describe('DocumentHistory', () => {
  let fixture: ComponentFixture<DocumentHistory>;
  let component: DocumentHistory;
  let api: ReturnType<typeof apiStub>;

  beforeEach(async () => {
    api = apiStub();
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:pdf') });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });

    await TestBed.configureTestingModule({
      imports: [DocumentHistory],
      providers: [
        MessageService,
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentHistory);
    fixture.componentRef.setInput('documentType', 'soa_report');
    fixture.componentRef.setInput('sourceArtifactId', 'soa-1');
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads signed document history for the selected artifact', () => {
    expect(api.listSignedDocuments).toHaveBeenCalledWith('soa_report', 'soa-1');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('WTN-SOA-0002');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Obsoleto');
  });

  it('downloads a signed PDF from history', () => {
    (component as unknown as { download(doc: SignedDocument): void }).download(SIGNED);

    expect(api.downloadSignedPdf).toHaveBeenCalledWith('signed-1');
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it('verifies document integrity and reports success', () => {
    const messages = TestBed.inject(MessageService);
    const add = vi.spyOn(messages, 'add');

    (component as unknown as { verify(doc: SignedDocument): void }).verify(SIGNED);

    expect(api.verifySignedDocument).toHaveBeenCalledWith('signed-1');
    expect(add).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      summary: 'Integridade confirmada',
      detail: 'WTN-SOA-0002',
    }));
  });
});
