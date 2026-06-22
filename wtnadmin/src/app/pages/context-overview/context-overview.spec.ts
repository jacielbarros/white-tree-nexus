import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';
import { ContextOverviewPage } from './context-overview';

const OVERVIEW = {
  analysis: { draft_status: 'in_review', current_version_id: null, review_overdue: false, issues: [{}, {}] },
  stakeholders: { draft_status: 'draft', current_version_id: null, review_overdue: false, stakeholders: [{}] },
  scope: {
    draft_status: 'draft',
    current_version_id: 'v1',
    review_overdue: true,
    items: [{}, {}, {}],
    context_ref_obsolete: true,
    stakeholder_ref_obsolete: false,
  },
};

const mockApi = {
  getContextOverview: vi.fn(() => of(OVERVIEW)),
  listSuggestions: vi.fn(() => of([{ id: 's1', target: 'stakeholder', payload: {}, reason: 'Adicionar parte X' }])),
  acceptSuggestion: vi.fn(() => of({})),
};

interface View {
  cards(): { key: string; status: string; count: number; overdue: boolean; alerts: string[] }[];
  approvedCount(): number;
}

describe('ContextOverviewPage', () => {
  let component: ContextOverviewPage;
  let view: View;

  beforeEach(async () => {
    mockApi.getContextOverview.mockClear();
    await TestBed.configureTestingModule({
      imports: [ContextOverviewPage],
      providers: [
        provideRouter([]),
        MessageService,
        { provide: ApiService, useValue: mockApi },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ContextOverviewPage);
    component = fixture.componentInstance;
    view = component as unknown as View;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('builds one card per Clause-4 artifact', () => {
    const keys = view.cards().map((c) => c.key);
    expect(keys).toEqual(['analysis', 'stakeholders', 'scope']);
  });

  it('maps draft_status / version / overdue to a normalized status', () => {
    const byKey = Object.fromEntries(view.cards().map((c) => [c.key, c]));
    expect(byKey['analysis'].status).toBe('Em revisão'); // in_review, sem versão
    expect(byKey['stakeholders'].status).toBe('Rascunho'); // draft, sem versão
    expect(byKey['scope'].status).toBe('Revisão vencida'); // versão vigente + review_overdue
    expect(byKey['scope'].overdue).toBe(true);
  });

  it('counts items and surfaces obsolete-reference alerts on scope', () => {
    const scope = view.cards().find((c) => c.key === 'scope')!;
    expect(scope.count).toBe(3);
    expect(scope.alerts).toContain('Referência de contexto obsoleta');
    expect(scope.alerts).not.toContain('Referência de partes obsoleta');
  });

  it('approvedCount counts only in-force artifacts', () => {
    expect(view.approvedCount()).toBe(0); // scope está "Revisão vencida", não "Em vigor"
  });

  it('loads heuristic suggestions', () => {
    expect(component['suggestions']().length).toBe(1);
  });
});
