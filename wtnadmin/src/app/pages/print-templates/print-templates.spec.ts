import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { PrintTemplate, PrintTemplateVersion } from '@app/core/models';
import { PrintTemplatesPage } from './print-templates';

const SYSTEM_TEMPLATE: PrintTemplate = {
  id: 'system-template-1',
  tenant_id: null,
  scope: 'system',
  document_type: 'context_report',
  name: 'Contexto padrao',
  description: 'Modelo do sistema',
  status: 'active',
  default_classification: 'uso_interno',
  current_version_id: 'system-version-1',
  created_at: '2026-06-23T17:00:00Z',
  updated_at: null,
};

const TENANT_TEMPLATE: PrintTemplate = {
  id: 'tenant-template-1',
  tenant_id: 'org-1',
  scope: 'tenant',
  document_type: 'gap_report',
  name: 'Gap customizado',
  description: null,
  status: 'active',
  default_classification: 'uso_interno',
  current_version_id: null,
  created_at: '2026-06-23T17:01:00Z',
  updated_at: null,
};

const VERSION: PrintTemplateVersion = {
  id: 'version-1',
  template_id: TENANT_TEMPLATE.id,
  version_number: 1,
  renderer: 'reportlab',
  layout_schema: { title: 'Gap' },
  allowed_variables: { required: ['organization_name'] },
  required_sections: ['summary'],
  content_hash: 'a'.repeat(64),
  is_current: true,
  created_at: '2026-06-23T17:02:00Z',
};

function apiStub() {
  return {
    listPrintTemplates: vi.fn(() => of([SYSTEM_TEMPLATE, TENANT_TEMPLATE])),
    createPrintTemplate: vi.fn(() => of({ ...TENANT_TEMPLATE, id: 'tenant-template-2', name: 'Novo Gap' })),
    createPrintTemplateVersion: vi.fn(() => of(VERSION)),
    activatePrintTemplateVersion: vi.fn(() => of({ ...TENANT_TEMPLATE, current_version_id: VERSION.id })),
  };
}

describe('PrintTemplatesPage', () => {
  let fixture: ComponentFixture<PrintTemplatesPage>;
  let component: PrintTemplatesPage;
  let api: ReturnType<typeof apiStub>;

  beforeEach(async () => {
    api = apiStub();
    await TestBed.configureTestingModule({
      imports: [PrintTemplatesPage],
      providers: [
        MessageService,
        { provide: ApiService, useValue: api },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PrintTemplatesPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads system and tenant templates', () => {
    expect(api.listPrintTemplates).toHaveBeenCalled();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Contexto padrao');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Gap customizado');
  });

  it('creates a tenant template with controlled metadata', () => {
    const form = (component as unknown as { templateForm: { patchValue(v: unknown): void } }).templateForm;
    form.patchValue({
      document_type: 'gap_report',
      name: 'Novo Gap',
      description: 'Template tenant',
      default_classification: 'confidencial',
    });

    (component as unknown as { createTemplate(): void }).createTemplate();

    expect(api.createPrintTemplate).toHaveBeenCalledWith({
      document_type: 'gap_report',
      name: 'Novo Gap',
      description: 'Template tenant',
      default_classification: 'confidencial',
    });
  });

  it('does not submit an empty template name', () => {
    const messages = TestBed.inject(MessageService);
    const add = vi.spyOn(messages, 'add');
    const form = (component as unknown as { templateForm: { patchValue(v: unknown): void } }).templateForm;
    form.patchValue({ name: '   ' });

    (component as unknown as { createTemplate(): void }).createTemplate();

    expect(api.createPrintTemplate).not.toHaveBeenCalled();
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: 'warn', summary: 'Nome obrigatorio' }));
  });

  it('creates and activates a new version for a tenant template', () => {
    (component as unknown as { createVersion(template: PrintTemplate): void }).createVersion(TENANT_TEMPLATE);

    expect(api.createPrintTemplateVersion).toHaveBeenCalledWith(TENANT_TEMPLATE.id, {
      layout_schema: expect.objectContaining({ title: 'Documento SGSI' }),
      allowed_variables: expect.objectContaining({ required: ['organization_name', 'document_title', 'generated_at'] }),
      required_sections: ['summary', 'items'],
    });
    expect(api.activatePrintTemplateVersion).toHaveBeenCalledWith(TENANT_TEMPLATE.id, VERSION.id);
  });

  it('does not create versions for system templates', () => {
    (component as unknown as { createVersion(template: PrintTemplate): void }).createVersion(SYSTEM_TEMPLATE);

    expect(api.createPrintTemplateVersion).not.toHaveBeenCalled();
  });
});
