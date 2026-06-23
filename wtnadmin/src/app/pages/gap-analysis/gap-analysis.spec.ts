import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { GapAnalysisPage } from './gap-analysis';
import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

describe('GapAnalysisPage', () => {
  let component: GapAnalysisPage;
  let store: AuthStore;

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

    store = TestBed.inject(AuthStore);
    store.setToken('fake-token');
    store.setMe({
      user_id: 'u1',
      email: 'admin@example.com',
      full_name: 'Admin',
      is_super_admin: false,
      memberships: [{ tenant_id: 'org1', org_name: 'Org', role: 'org_admin' }],
    });
    store.setActiveOrg('org1');

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

  it('renders expected evidence and attached evidence as separate sections with empty state', () => {
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const comp = fixture.componentInstance as never as {
      loading: { set(v: boolean): void };
      assessment: { set(v: unknown): void };
      guidanceByRef: { set(v: unknown): void };
      evidences: { set(v: unknown): void };
      evidenceLoading: { set(v: boolean): void };
      selectItem(i: unknown): void;
    };
    fixture.detectChanges();
    const item = { id: '1', ref_code: 'A.5.1', name: 'Políticas', status: 'not_filled', dimension: 'annex_a' };
    comp.assessment.set({ id: 'a', draft_status: 'draft', current_version_id: null, items: [item] });
    comp.guidanceByRef.set({
      'A.5.1': {
        seed_item_id: 's1', ref_code: 'A.5.1', referencia: 'ISO',
        objetivo: 'Objetivo', como_avaliar: [],
        evidencias_esperadas: ['Política aprovada'], nota: null,
      },
    });
    comp.selectItem(item);
    comp.evidences.set([]);
    comp.evidenceLoading.set(false);
    comp.loading.set(false);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Evidências esperadas');
    expect(el.textContent).toContain('Evidências anexadas');
    expect(el.textContent).toContain('Nenhuma evidência anexada ainda.');
  });

  it('submits upload FormData with file, description and classification', () => {
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const api = TestBed.inject(ApiService);
    const created = {
      id: 'ev1', assessment_item_id: '1', title: 'policy.pdf', description: 'desc',
      classification: 'uso_interno', status: 'active', current_version_id: 'v1',
      file_name: 'policy.pdf', mime_type: 'application/pdf', extension: '.pdf',
      size_bytes: 7, content_hash: 'a'.repeat(64), hash_algorithm: 'sha256',
      uploaded_by: 'u1', uploaded_at: new Date().toISOString(), created_at: new Date().toISOString(),
      can_download: true,
    };
    const post = vi.spyOn(api, 'postForm').mockReturnValue(of(created) as never);
    const comp = fixture.componentInstance as never as {
      selectedItem: { set(v: unknown): void };
      selectedEvidenceFile: { set(v: File): void };
      evidenceDescription: { setValue(v: string): void };
      evidenceClassification: { setValue(v: string): void };
      uploadEvidence(): void;
    };
    comp.selectedItem.set({ id: '1' });
    comp.selectedEvidenceFile.set(new File(['content'], 'policy.pdf', { type: 'application/pdf' }));
    comp.evidenceDescription.setValue('desc');
    comp.evidenceClassification.setValue('uso_interno');

    comp.uploadEvidence();

    expect(post).toHaveBeenCalledOnce();
    const [path, form] = post.mock.calls[0];
    expect(path).toBe('/gap/assessment/items/1/evidences');
    expect(form.get('file')).toBeTruthy();
    expect(form.get('description')).toBe('desc');
    expect(form.get('classification')).toBe('uso_interno');
  });

  it('shows upload and custody actions only for manage_gap users', () => {
    store.setMe({
      user_id: 'u2',
      email: 'client@example.com',
      full_name: 'Client',
      is_super_admin: false,
      memberships: [{ tenant_id: 'org1', org_name: 'Org', role: 'client' }],
    });
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const comp = fixture.componentInstance as never as {
      loading: { set(v: boolean): void };
      assessment: { set(v: unknown): void };
      evidences: { set(v: unknown): void };
      evidenceLoading: { set(v: boolean): void };
      selectItem(i: unknown): void;
    };
    fixture.detectChanges();
    const item = { id: '1', ref_code: 'A.5.1', name: 'Políticas', status: 'not_filled', dimension: 'annex_a' };
    const evidence = {
      id: 'ev1', assessment_item_id: '1', title: 'policy.pdf', description: null,
      classification: 'uso_interno', status: 'active', current_version_id: 'v1',
      file_name: 'policy.pdf', mime_type: 'application/pdf', extension: '.pdf',
      size_bytes: 7, content_hash: 'a'.repeat(64), hash_algorithm: 'sha256',
      uploaded_by: 'u1', uploaded_at: new Date().toISOString(), created_at: new Date().toISOString(),
      can_download: true,
    };
    comp.assessment.set({ id: 'a', draft_status: 'draft', current_version_id: null, items: [item] });
    comp.selectItem(item);
    comp.evidences.set([evidence]);
    comp.evidenceLoading.set(false);
    comp.loading.set(false);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).not.toContain('Adicionar evidência');
    expect(el.querySelector('.icon-action--download')).toBeTruthy();
    expect(el.querySelector('.icon-action--history')).toBeFalsy();
    expect(el.querySelector('.icon-action--replace')).toBeFalsy();
    expect(el.querySelector('.icon-action--delete')).toBeFalsy();
  });

  it('renders download action only when the API marks evidence as downloadable', () => {
    const fixture = TestBed.createComponent(GapAnalysisPage);
    const comp = fixture.componentInstance as never as {
      loading: { set(v: boolean): void };
      assessment: { set(v: unknown): void };
      evidences: { set(v: unknown): void };
      evidenceLoading: { set(v: boolean): void };
      selectItem(i: unknown): void;
    };
    fixture.detectChanges();
    const item = { id: '1', ref_code: 'A.5.1', name: 'Políticas', status: 'not_filled', dimension: 'annex_a' };
    const base = {
      assessment_item_id: '1', title: 'policy.pdf', description: null,
      classification: 'uso_interno', status: 'active', current_version_id: 'v1',
      file_name: 'policy.pdf', mime_type: 'application/pdf', extension: '.pdf',
      size_bytes: 7, content_hash: 'a'.repeat(64), hash_algorithm: 'sha256',
      uploaded_by: 'u1', uploaded_at: new Date().toISOString(), created_at: new Date().toISOString(),
    };
    comp.assessment.set({ id: 'a', draft_status: 'draft', current_version_id: null, items: [item] });
    comp.selectItem(item);
    comp.evidences.set([
      { ...base, id: 'ev1', can_download: true },
      { ...base, id: 'ev2', can_download: false, file_name: 'secret.pdf' },
    ]);
    comp.evidenceLoading.set(false);
    comp.loading.set(false);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelectorAll('.icon-action--download').length).toBe(1);
    expect(el.querySelector('.icon-action--download svg')).toBeTruthy();
    expect(el.querySelector('.icon-action--download')?.getAttribute('aria-label')).toBe('Baixar evidencia');
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
