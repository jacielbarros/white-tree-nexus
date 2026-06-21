import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { SoaPage } from './soa';
import { AuthStore } from '@app/core/auth.store';

describe('SoaPage', () => {
  let component: SoaPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SoaPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), MessageService],
    }).compileComponents();

    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(SoaPage).componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('starts with no SoA and loading', () => {
    expect(component.soa()).toBeNull();
    expect(component.loading()).toBe(true);
  });

  it('themes() is empty without data', () => {
    expect(component.themes()).toEqual([]);
  });

  it('statusLabel maps known codes', () => {
    expect(component.statusLabel('implemented')).toBe('Implementado');
    expect(component.statusLabel('not_started')).toBe('Não iniciado');
  });

  it('themeLabel maps annex themes', () => {
    expect(component.themeLabel('technological')).toContain('A.8');
  });

  it('toggleReason adds and removes', () => {
    component.toggleReason('legal');
    expect(component.editReasons()).toContain('legal');
    component.toggleReason('legal');
    expect(component.editReasons()).not.toContain('legal');
  });

  it('dialog starts closed', () => {
    expect(component.dialogVisible).toBe(false);
  });
});
