import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { AssetsPage } from './assets';
import { AuthStore } from '@app/core/auth.store';

describe('AssetsPage', () => {
  let component: AssetsPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetsPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), MessageService],
    }).compileComponents();

    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(AssetsPage).componentInstance;
  });

  it('should create and start loading', () => {
    expect(component).toBeTruthy();
    expect(component.loading()).toBe(true);
  });

  it('builds type/scope/cia options', () => {
    expect(component.typeOptions.length).toBe(11);
    expect(component.scopeOptions.map((o) => o.value)).toContain('in_scope');
    expect(component.ciaOptions.map((o) => o.value)).toEqual(['baixa', 'media', 'alta', 'critica']);
  });

  it('maps labels and tag classes', () => {
    expect(component.typeLabel('supplier')).toBe('Fornecedor/terceiro');
    expect(component.scopeLabel('in_scope')).toBe('Dentro do escopo');
    expect(component.scopeClass('in_scope')).toBe('wtn-tag--success');
    expect(component.scopeClass('under_analysis')).toBe('wtn-tag--warning');
    expect(component.reviewClass('overdue')).toBe('wtn-tag--danger');
  });

  it('opens create dialog with defaults', () => {
    component.openCreate();
    expect(component.dialogVisible()).toBe(true);
    expect(component.form.value.item_type).toBe('information_asset');
    expect(component.form.value.scope_status).toBe('under_analysis');
  });

  it('fromContext prefills the form', () => {
    component.contextSources.set([
      { origin_type: 'stakeholder', origin_id: 'x', label: 'Fornecedor Cloud', description: 'desc', suggested_item_type: 'supplier' },
    ]);
    component.fromContext('0');
    expect(component.dialogVisible()).toBe(true);
    expect(component.form.value.name).toBe('Fornecedor Cloud');
    expect(component.form.value.item_type).toBe('supplier');
  });
});
