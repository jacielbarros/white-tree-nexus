import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { ContextAnalysisPage } from './context-analysis';

const ANALYSIS = {
  id: 'analysis-1',
  intended_outcomes: 'Resultados pretendidos',
  methodology: 'PESTEL + SWOT',
  draft_status: 'draft',
  current_version_id: null,
  review_overdue: false,
  issues: [
    {
      id: 'issue-1',
      origin: 'external',
      framework: 'pestel',
      nature: 'threat',
      category: 'Legal',
      description: 'LGPD aplicavel',
      impact: 'alto',
    },
  ],
};

const mockApi = {
  getContextAnalysis: vi.fn(() => of(ANALYSIS)),
  saveContextAnalysis: vi.fn(() => of(ANALYSIS)),
  createContextIssue: vi.fn(() => of({})),
  deleteContextIssue: vi.fn(() => of(void 0)),
  submitContextAnalysis: vi.fn(() => of(ANALYSIS)),
  approveContextAnalysis: vi.fn(() => of({})),
};

interface View {
  analysis(): typeof ANALYSIS | null;
  issueForm: {
    controls: {
      origin: { value: string };
      framework: { value: string };
      nature: { value: string };
      category: { value: string };
      description: { value: string };
      impact: { value: string };
    };
  };
  applyPreset(value: string): void;
  deleteIssue(id: string): void;
}

describe('ContextAnalysisPage', () => {
  let component: ContextAnalysisPage;
  let view: View;
  let nativeElement: HTMLElement;

  beforeEach(async () => {
    vi.restoreAllMocks();
    mockApi.getContextAnalysis.mockClear();
    mockApi.deleteContextIssue.mockClear();

    await TestBed.configureTestingModule({
      imports: [ContextAnalysisPage],
      providers: [{ provide: ApiService, useValue: mockApi }],
    }).compileComponents();

    const fixture = TestBed.createComponent(ContextAnalysisPage);
    component = fixture.componentInstance;
    view = component as unknown as View;
    fixture.detectChanges();
    nativeElement = fixture.nativeElement as HTMLElement;
  });

  it('carrega a analise de contexto com questoes existentes', () => {
    expect(component).toBeTruthy();
    expect(view.analysis()?.issues.length).toBe(1);
    expect(view.analysis()?.issues[0].category).toBe('Legal');
    expect(nativeElement.textContent).toContain('Excluir');
  });

  it('aplica presets PESTEL preenchendo origem, framework e categoria', () => {
    view.applyPreset('pestel-economica');

    expect(view.issueForm.controls.origin.value).toBe('external');
    expect(view.issueForm.controls.framework.value).toBe('pestel');
    expect(view.issueForm.controls.nature.value).toBe('contextual');
    expect(view.issueForm.controls.category.value).toBe('Economica');
    expect(view.issueForm.controls.description.value).toContain('Custos de nuvem');
    expect(view.issueForm.controls.impact.value).toBe('medio');
  });

  it('exclui questao usando o endpoint existente', () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true);

    view.deleteIssue('issue-1');

    expect(mockApi.deleteContextIssue).toHaveBeenCalledWith('issue-1');
    expect(mockApi.getContextAnalysis).toHaveBeenCalledTimes(2);
  });
});
