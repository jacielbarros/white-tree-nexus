import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';

import { RiskCatalogPage } from './risk-catalog';
import { AuthStore } from '@app/core/auth.store';

describe('RiskCatalogPage', () => {
  let component: RiskCatalogPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RiskCatalogPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(RiskCatalogPage).componentInstance;
  });

  it('creates and defaults to the threats tab', () => {
    expect(component).toBeTruthy();
    expect(component.tab()).toBe('threats');
  });

  it('translates category labels', () => {
    expect(component.threatCatLabel('human')).toBe('Humana');
    expect(component.vulnCatLabel('technical')).toBe('Técnica');
  });
});
