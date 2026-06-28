import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';

import { RiskMethodologyPage } from './risk-methodology';
import { AuthStore } from '@app/core/auth.store';
import type { RiskMethodology } from '@app/core/models';

function methodology(): RiskMethodology {
  return {
    is_configured: false,
    probability_scale: [], impact_scale: [],
    risk_levels: [
      { key: 'low', label: 'Baixo', severity: 1, color: '#2e7d32', order: 1 },
      { key: 'high', label: 'Alto', severity: 3, color: '#ef6c00', order: 3 },
    ],
    risk_matrix: { '1x1': 'low', '5x5': 'high' },
    acceptance: { low: true, high: false },
    cia_impact_map: { baixa: 2, media: 3, alta: 4, critica: 5 },
  };
}

describe('RiskMethodologyPage', () => {
  let component: RiskMethodologyPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskMethodologyPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(RiskMethodologyPage).componentInstance;
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('mutates matrix/acceptance/cia immutably via setters', () => {
    const m = methodology();
    component.setCell(m, 1, 1, 'high');
    expect(component.m()?.risk_matrix['1x1']).toBe('high');
    component.setAcceptance(component.m()!, 'high', true);
    expect(component.m()?.acceptance['high']).toBe(true);
    component.setCia(component.m()!, 'critica', 4);
    expect(component.m()?.cia_impact_map['critica']).toBe(4);
    expect(component.cellColor(component.m()!, 5, 5)).toBe('#ef6c00');
  });
});
