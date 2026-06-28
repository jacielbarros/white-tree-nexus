import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach } from 'vitest';

import { RiskDetailPage } from './risk-detail';
import { AuthStore } from '@app/core/auth.store';

describe('RiskDetailPage', () => {
  let component: RiskDetailPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskDetailPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(RiskDetailPage).componentInstance;
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('maps level/status/treatment labels', () => {
    expect(component.level('critical')).toBe('Crítico');
    expect(component.statusLabel('in_treatment')).toBe('Em tratamento');
    expect(component.treatmentLabel('mitigate')).toBe('Mitigar');
  });

  it('resolves gap control name from loaded catalog', () => {
    component.gapControls.set([{ id: 'g1', ref_code: 'A.5.1', name: 'Políticas', dimension: 'annex_a' }]);
    expect(component.gapName('g1')).toBe('A.5.1 · Políticas');
    expect(component.gapName(null)).toBe('—');
  });
});
