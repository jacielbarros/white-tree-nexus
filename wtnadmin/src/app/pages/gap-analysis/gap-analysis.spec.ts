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
});
