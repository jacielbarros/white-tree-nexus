import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapAnalysisPage } from './gap-analysis';
import { AuthStore } from '@app/core/auth.store';

describe('GapAnalysisPage', () => {
  let component: GapAnalysisPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GapAnalysisPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
      ],
    }).compileComponents();

    const store = TestBed.inject(AuthStore);
    store.setToken('fake-token');

    const fixture = TestBed.createComponent(GapAnalysisPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start loading', () => {
    expect(component.loading()).toBe(true);
  });

  it('completeness/totalItems are 0 without assessment', () => {
    expect(component.completeness()).toBe(0);
    expect(component.totalItems()).toBe(0);
  });

  it('statusLabel returns the PT-BR label', () => {
    expect(component.statusLabel('meets')).toBe('Atende');
    expect(component.statusLabel('not_filled')).toBe('Não avaliado');
    expect(component.statusLabel('not_applicable')).toBe('N/A');
  });

  it('derives totalItems and completeness from the assessment', () => {
    component.assessment.set({
      id: 'a1',
      draft_status: 'draft',
      current_version_id: null,
      items: [
        { id: '1', ref_code: 'A.5.1', name: 'x', status: 'meets', dimension: 'annex_a' },
        { id: '2', ref_code: 'A.5.2', name: 'y', status: 'not_filled', dimension: 'annex_a' },
      ],
    } as never);
    expect(component.totalItems()).toBe(2);
    expect(component.completeness()).toBe(0.5);
  });

  it('statusClass maps each status to a wtn-tag modifier', () => {
    const cls = component as unknown as { statusClass(s: string): string };
    expect(cls.statusClass('meets')).toBe('wtn-tag--success');
    expect(cls.statusClass('not_meet')).toBe('wtn-tag--danger');
    expect(cls.statusClass('partial')).toBe('wtn-tag--warning');
  });

  it('renders the per-item guidance in the panel (US1)', () => {
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const comp = fixture.componentInstance as never as {
      loading: { set(v: boolean): void };
      assessment: { set(v: unknown): void };
      guidanceByRef: { set(v: unknown): void };
      selectItem(i: unknown): void;
    };
    const item = { id: '1', ref_code: 'A.8.24', name: 'Uso de criptografia', status: 'not_filled', dimension: 'annex_a' };
    fixture.detectChanges(); // dispara ngOnInit (load() seta loading=true; HTTP não é resolvido nos testes)
    comp.assessment.set({ id: 'a', draft_status: 'draft', current_version_id: null, items: [item] });
    comp.guidanceByRef.set({
      'A.8.24': {
        seed_item_id: 's1', ref_code: 'A.8.24', referencia: 'ISO/IEC 27001:2022 — A.8.24',
        objetivo: 'Regras para uso de criptografia.', como_avaliar: ['Existe política de criptografia?'],
        evidencias_esperadas: ['Política de criptografia'], nota: null,
      },
    });
    comp.selectItem(item);
    comp.loading.set(false); // depois do ngOnInit, libera a renderização da matriz/painel
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.guidance-block')).toBeTruthy();
    expect(el.textContent).toContain('Como avaliar');
    expect(el.textContent).toContain('Existe política de criptografia?');
    expect(el.textContent).toContain('Política de criptografia');
  });

  it('renders the global legend when present (US3)', () => {
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const comp = fixture.componentInstance as never as {
      legendStatus: { set(v: unknown): void };
      legendPriority: { set(v: unknown): void };
    };
    comp.legendStatus.set([{ code: 'meets', label: 'Atende Totalmente', definition: 'Implementado e evidenciado.', order: 3 }]);
    comp.legendPriority.set([{ code: 'critical', label: 'Crítica', definition: 'Inviabiliza a certificação.', order: 1 }]);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.wtn-legend')).toBeTruthy();
    expect(el.textContent).toContain('Atende Totalmente');
    expect(el.textContent).toContain('Crítica');
  });
});
