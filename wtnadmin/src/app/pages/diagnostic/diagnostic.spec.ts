import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { DiagnosticPage } from './diagnostic';

const mockApi = {
  listTemplates: () =>
    of([
      { id: 't1', kind: 'diagnostic', status: 'active', title: 'Diag ativo', schema: [{}, {}] },
      { id: 't2', kind: 'diagnostic', status: 'archived', title: 'Diag arquivado', schema: [] },
      { id: 't3', kind: 'generic', status: 'active', title: 'Genérico', schema: [] },
    ]),
  listAssignments: () =>
    of([
      { id: 'a1', kind: 'diagnostic', status: 'completed', respondent_email: 'x@y.com', deadline_at: null },
      { id: 'a2', kind: 'gap_analysis', status: 'pending', respondent_email: null, deadline_at: null },
    ]),
  getDiagnostic: () =>
    of({
      status: 'completed',
      sections: {
        form_intake: {
          source: 'workflow',
          assignment_id: 'a1',
          completed_at: '2026-06-01T12:00:00Z',
          answers: { possui_politica: true, escopo: 'TI corporativa', terceiros: false },
        },
      },
    }),
};

interface View {
  diagTemplates(): { id: string }[];
  diagAssignments(): { id: string }[];
  intake(): { source: string; answers: { key: string; value: string }[] } | null;
  templateClass(s: string): string;
  templateLabel(s: string): string;
}

describe('DiagnosticPage', () => {
  let component: DiagnosticPage;
  let view: View;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DiagnosticPage],
      providers: [provideRouter([]), { provide: ApiService, useValue: mockApi }],
    }).compileComponents();

    const fixture = TestBed.createComponent(DiagnosticPage);
    component = fixture.componentInstance;
    view = component as unknown as View;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('keeps only non-archived diagnostic templates', () => {
    expect(view.diagTemplates().map((t) => t.id)).toEqual(['t1']);
  });

  it('keeps only diagnostic assignments', () => {
    expect(view.diagAssignments().map((a) => a.id)).toEqual(['a1']);
  });

  it('maps template status to tag label/class', () => {
    expect(view.templateLabel('active')).toBe('Ativo');
    expect(view.templateClass('archived')).toBe('wtn-tag--danger');
  });

  it('parses the form_intake into the current diagnostic, formatting booleans', () => {
    const intake = view.intake()!;
    expect(intake.source).toBe('workflow');
    const byKey = Object.fromEntries(intake.answers.map((a) => [a.key, a.value]));
    expect(byKey['possui_politica']).toBe('Sim');
    expect(byKey['terceiros']).toBe('Não');
    expect(byKey['escopo']).toBe('TI corporativa');
  });
});
