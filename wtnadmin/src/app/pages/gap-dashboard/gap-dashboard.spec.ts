import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapDashboardPage } from './gap-dashboard';
import { AuthStore } from '@app/core/auth.store';

describe('GapDashboardPage', () => {
  let component: GapDashboardPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GapDashboardPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
      ],
    }).compileComponents();

    const store = TestBed.inject(AuthStore);
    store.setToken('fake-token');

    const fixture = TestBed.createComponent(GapDashboardPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start loading', () => {
    expect(component.loading()).toBe(true);
  });

  it('dashboard signal starts null', () => {
    expect(component.dashboard()).toBeNull();
  });

  it('statusLabel maps correctly', () => {
    expect(component.statusLabel('meets')).toBe('Atende');
    expect(component.statusLabel('partial')).toBe('Parcialmente atende');
    expect(component.statusLabel('not_meet')).toBe('Não atende');
    expect(component.statusLabel('not_applicable')).toBe('N/A');
    expect(component.statusLabel('not_filled')).toBe('Não avaliado');
  });

  it('dimLabel maps correctly', () => {
    expect(component.dimLabel('clause')).toBe('Cláusulas (4–10)');
    expect(component.dimLabel('annex_a')).toBe('Anexo A — Controles');
  });

  it('prioritySeverity maps correctly', () => {
    expect(component.prioritySeverity('critical')).toBe('danger');
    expect(component.prioritySeverity('high')).toBe('warn');
    expect(component.prioritySeverity('medium')).toBe('info');
    expect(component.prioritySeverity('low')).toBe('secondary');
    expect(component.prioritySeverity('unknown')).toBe('secondary');
  });

  it('statusEntries returns empty array without dashboard', () => {
    expect(component.statusEntries()).toEqual([]);
  });

  it('dimensionEntries returns empty array without dashboard', () => {
    expect(component.dimensionEntries()).toEqual([]);
  });
});
