import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { SoaVersionsPage } from './soa-versions';
import { AuthStore } from '@app/core/auth.store';

describe('SoaVersionsPage', () => {
  let component: SoaVersionsPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SoaVersionsPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), MessageService],
    }).compileComponents();

    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(SoaVersionsPage).componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('starts empty', () => {
    expect(component.soa()).toBeNull();
    expect(component.versions()).toEqual([]);
    expect(component.incomplete()).toEqual([]);
  });

  it('approve dialog starts closed', () => {
    expect(component.approveVisible).toBe(false);
  });

  it('showApprove sets defaults (initial emission)', () => {
    component.showApprove();
    expect(component.approveVisible).toBe(true);
    expect(component.approveClassification).toBe('uso_interno');
    expect(component.approveNature).toBe('Emissão inicial');
    expect(component.approveSign).toBe(false);
  });

  it('has classification options', () => {
    expect(component.classificationOptions.length).toBe(4);
  });
});
