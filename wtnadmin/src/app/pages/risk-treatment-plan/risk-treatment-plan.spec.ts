import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';

import { RiskTreatmentPlanPage } from './risk-treatment-plan';
import { AuthStore } from '@app/core/auth.store';

describe('RiskTreatmentPlanPage', () => {
  let component: RiskTreatmentPlanPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskTreatmentPlanPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(RiskTreatmentPlanPage).componentInstance;
  });

  it('creates', () => {
    expect(component).toBeTruthy();
  });

  it('translates draft status labels', () => {
    expect(component.statusLabel('draft')).toBe('Rascunho');
    expect(component.statusLabel('in_review')).toBe('Em revisão');
    expect(component.statusLabel('in_force')).toBe('Em vigor');
  });
});
