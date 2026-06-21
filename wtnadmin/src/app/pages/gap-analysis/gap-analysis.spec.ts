import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapAnalysisPage } from './gap-analysis';
import { AuthStore } from '@app/core/auth.store';

describe('GapAnalysisPage', () => {
  let component: GapAnalysisPage;
  let ref: ComponentRef<GapAnalysisPage>;

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
    ref = fixture.componentRef;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start loading', () => {
    expect(component.loading()).toBe(true);
  });

  it('completeness returns 0 when no items', () => {
    expect(component.completeness()).toBe(0);
  });

  it('totalItems returns 0 when no assessment', () => {
    expect(component.totalItems()).toBe(0);
  });

  it('statusLabel returns correct label', () => {
    expect(component.statusLabel('meets')).toBe('Atende');
    expect(component.statusLabel('not_filled')).toBe('Não avaliado');
    expect(component.statusLabel('not_applicable')).toBe('N/A');
  });

  it('statusSeverity returns correct severity', () => {
    expect(component.statusSeverity('meets')).toBe('success');
    expect(component.statusSeverity('not_meet')).toBe('danger');
    expect(component.statusSeverity('not_filled')).toBe('secondary');
  });

  it('dimLabel returns correct label', () => {
    expect(component.dimLabel('clause')).toBe('Cláusulas (4–10)');
    expect(component.dimLabel('annex_a')).toBe('Anexo A — Controles');
  });
});
