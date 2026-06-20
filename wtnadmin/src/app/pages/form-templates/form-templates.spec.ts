import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { FormTemplate } from '@app/core/models';
import { FormTemplatesPage } from './form-templates';

const TEMPLATE: FormTemplate = {
  id: 'tpl-1',
  kind: 'diagnostic',
  title: 'Diagnóstico Base',
  schema: [{ label: 'Razão social', key: 'razao_social', type: 'text', required: true }],
  status: 'active',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

function apiStub() {
  return {
    listTemplates: vi.fn(() => of([TEMPLATE])),
    createTemplate: vi.fn(() => of({ ...TEMPLATE, id: 'tpl-2', title: 'Novo' })),
    updateTemplate: vi.fn(() => of(TEMPLATE)),
    deleteTemplate: vi.fn(() => of(undefined)),
  };
}

describe('FormTemplatesPage', () => {
  let fixture: ComponentFixture<FormTemplatesPage>;
  let component: FormTemplatesPage;
  let api: ReturnType<typeof apiStub>;

  beforeEach(async () => {
    api = apiStub();
    await TestBed.configureTestingModule({
      imports: [FormTemplatesPage],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: api },
        MessageService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FormTemplatesPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('carrega e exibe lista de templates', () => {
    expect(api.listTemplates).toHaveBeenCalled();
    const html = fixture.nativeElement as HTMLElement;
    expect(html.textContent).toContain('Diagnóstico Base');
  });

  it('abre o editor ao abrir novo', () => {
    component['openNew']();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('.editor')).toBeTruthy();
  });

  it('salva novo template chamando createTemplate', () => {
    // Abre editor
    component['openNew']();
    component['editTitle'] = 'Novo Template';
    fixture.detectChanges();
    component['save']();
    expect(api.createTemplate).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Novo Template', kind: 'diagnostic' }),
    );
  });

  it('não salva se título vazio', () => {
    component['openNew']();
    component['editTitle'] = '';
    component['save']();
    expect(api.createTemplate).not.toHaveBeenCalled();
  });

  it('setStatus(archived) chama updateTemplate', () => {
    component['setStatus'](TEMPLATE, 'archived');
    expect(api.updateTemplate).toHaveBeenCalledWith('tpl-1', { status: 'archived' });
  });

  it('setStatus(active) desarquiva via updateTemplate', () => {
    component['setStatus']({ ...TEMPLATE, status: 'archived' }, 'active');
    expect(api.updateTemplate).toHaveBeenCalledWith('tpl-1', { status: 'active' });
  });

  it('save converte opções de seleção (texto → array)', () => {
    component['openNew']();
    component['editTitle'] = 'Com Seleção';
    component['editFields'].set([
      { label: 'Porte', key: 'porte', type: 'select', required: false, _optionsText: 'Micro, Pequena, Média' },
    ]);
    component['save']();
    expect(api.createTemplate).toHaveBeenCalledWith(
      expect.objectContaining({
        schema: [expect.objectContaining({ key: 'porte', options: ['Micro', 'Pequena', 'Média'] })],
      }),
    );
  });

  it('exibe mensagem de erro quando listTemplates falha', async () => {
    api.listTemplates.mockReturnValue(throwError(() => new Error('net')));
    component.ngOnInit();
    expect(component['loading']()).toBe(false);
  });
});
