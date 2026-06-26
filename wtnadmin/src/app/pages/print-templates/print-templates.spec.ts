import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { PrintTemplate, PrintTemplateVariable, PrintTemplateVersion } from '@app/core/models';
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

const VARIABLES: PrintTemplateVariable[] = [
  {
    id: 'variable-organization',
    tenant_id: null,
    scope: 'system',
    document_type: 'gap_report',
    variable_key: 'organization_name',
    label: 'Organizacao',
    description: 'Nome da organizacao',
    value_type: 'string',
    required_by_default: true,
    optional_by_default: false,
    status: 'active',
    sort_order: 10,
    created_at: '2026-06-23T17:00:00Z',
    updated_at: null,
  },
  {
    id: 'variable-title',
    tenant_id: null,
    scope: 'system',
    document_type: 'gap_report',
    variable_key: 'document_title',
    label: 'Titulo',
    description: 'Titulo do documento',
    value_type: 'string',
    required_by_default: true,
    optional_by_default: false,
    status: 'active',
    sort_order: 20,
    created_at: '2026-06-23T17:00:00Z',
    updated_at: null,
  },
  {
    id: 'variable-generated',
    tenant_id: null,
    scope: 'system',
    document_type: 'gap_report',
    variable_key: 'generated_at',
    label: 'Data de geracao',
    description: 'Data',
    value_type: 'datetime',
    required_by_default: true,
    optional_by_default: false,
    status: 'active',
    sort_order: 30,
    created_at: '2026-06-23T17:00:00Z',
    updated_at: null,
  },
  {
    id: 'variable-classification',
    tenant_id: null,
    scope: 'system',
    document_type: 'gap_report',
    variable_key: 'classification',
    label: 'Classificacao',
    description: 'Classificacao do documento',
    value_type: 'string',
    required_by_default: false,
    optional_by_default: true,
    status: 'active',
    sort_order: 40,
    created_at: '2026-06-23T17:00:00Z',
    updated_at: null,
  },
];

function apiStub() {
  return {
    listPrintTemplates: vi.fn(() => of([SYSTEM_TEMPLATE, TENANT_TEMPLATE])),
    listPrintTemplateVariables: vi.fn(() => of(VARIABLES)),
    createPrintTemplate: vi.fn(() => of({ ...TENANT_TEMPLATE, id: 'tenant-template-2', name: 'Novo Gap' })),
    createPrintTemplateVariable: vi.fn((payload: Partial<PrintTemplateVariable>) => of({
      id: 'variable-custom',
      tenant_id: 'org-1',
      scope: 'tenant',
      document_type: payload.document_type ?? 'gap_report',
      variable_key: payload.variable_key ?? 'audit_cycle',
      label: payload.label ?? 'Ciclo de auditoria',
      description: payload.description ?? null,
      value_type: payload.value_type ?? 'string',
      required_by_default: false,
      optional_by_default: true,
      status: 'active',
      sort_order: 500,
      created_at: '2026-06-23T17:03:00Z',
      updated_at: null,
    } satisfies PrintTemplateVariable)),
    deactivatePrintTemplateVariable: vi.fn((id: string) => of({
      ...VARIABLES[0],
      id,
      scope: 'tenant',
      tenant_id: 'org-1',
      status: 'inactive',
    } satisfies PrintTemplateVariable)),
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
    expect(api.listPrintTemplateVariables).toHaveBeenCalledWith('gap_report');
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
      layout_schema: expect.objectContaining({
        title: 'Relatorio de Gap Analysis',
        sections: expect.arrayContaining([
          expect.objectContaining({ key: 'summary', title: 'Resumo de aderencia' }),
          expect.objectContaining({ key: 'items', title: 'Matriz de controles' }),
        ]),
        signature_appearance: expect.objectContaining({
          default_page: 'last',
          default_anchor: 'bottom_right',
          default_width_points: 180,
          default_height_points: 54,
        }),
      }),
      allowed_variables: expect.objectContaining({ required: ['organization_name', 'document_title', 'generated_at'] }),
      required_sections: ['summary', 'items'],
    });
    expect(api.activatePrintTemplateVersion).toHaveBeenCalledWith(TENANT_TEMPLATE.id, VERSION.id);
  });

  it('builds versions from guided section and variable choices', () => {
    const page = component as unknown as {
      select(template: PrintTemplate): void;
      toggleSection(key: string, checked: boolean): void;
      toggleVariable(key: string, type: 'required' | 'optional', checked: boolean): void;
      createVersion(template: PrintTemplate): void;
    };
    page.select(TENANT_TEMPLATE);
    page.toggleSection('gaps', false);
    page.toggleVariable('classification', 'required', true);

    page.createVersion(TENANT_TEMPLATE);

    const createVersionCall = api.createPrintTemplateVersion as unknown as {
      mock: {
        calls: Array<[string, {
          layout_schema: { sections: Array<{ key: string }> };
          allowed_variables: { required: string[]; optional: string[] };
        }]>;
      };
    };
    const payload = createVersionCall.mock.calls[0][1];
    expect(payload.layout_schema.sections).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ key: 'gaps' })]),
    );
    expect(payload.allowed_variables.required).toContain('classification');
    expect(payload.allowed_variables.optional).not.toContain('classification');
  });

  it('creates tenant variables from the catalog form', () => {
    const page = component as unknown as {
      select(template: PrintTemplate): void;
      variableForm: { patchValue(v: unknown): void };
      createVariable(template: PrintTemplate): void;
    };
    page.select(TENANT_TEMPLATE);
    page.variableForm.patchValue({
      variable_key: 'audit_cycle',
      label: 'Ciclo de auditoria',
      description: 'Janela usada no relatorio',
      value_type: 'string',
      optional_by_default: true,
    });

    page.createVariable(TENANT_TEMPLATE);

    expect(api.createPrintTemplateVariable).toHaveBeenCalledWith(expect.objectContaining({
      document_type: 'gap_report',
      variable_key: 'audit_cycle',
      label: 'Ciclo de auditoria',
      optional_by_default: true,
    }));
  });

  it('does not create versions for system templates', () => {
    (component as unknown as { createVersion(template: PrintTemplate): void }).createVersion(SYSTEM_TEMPLATE);

    expect(api.createPrintTemplateVersion).not.toHaveBeenCalled();
  });
});
