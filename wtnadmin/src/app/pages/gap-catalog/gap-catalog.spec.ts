import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapCatalogPage } from './gap-catalog';
import { AuthStore } from '@app/core/auth.store';

describe('GapCatalogPage', () => {
  let component: GapCatalogPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GapCatalogPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
      ],
    }).compileComponents();

    const store = TestBed.inject(AuthStore);
    store.setToken('fake-token');

    const fixture = TestBed.createComponent(GapCatalogPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should start loading', () => {
    expect(component.loading()).toBe(true);
  });

  it('items signal starts empty', () => {
    expect(component.items()).toEqual([]);
  });

  it('dimLabel maps correctly', () => {
    expect(component.dimLabel('clause')).toBe('Cláusulas (4–10)');
    expect(component.dimLabel('annex_a')).toBe('Anexo A — Controles');
  });

  it('dimensions computed returns empty when no items', () => {
    expect(component.dimensions()).toEqual([]);
  });

  it('form invalid when required fields empty', () => {
    expect(component.form.invalid).toBe(true);
  });

  it('form valid when required fields filled', () => {
    component.form.patchValue({ ref_code: 'A.5.1', dimension: 'annex_a', name: 'Test Control' });
    expect(component.form.valid).toBe(true);
  });
});
