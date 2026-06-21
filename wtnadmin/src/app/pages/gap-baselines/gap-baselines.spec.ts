import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { GapBaselinesPage } from './gap-baselines';
import { AuthStore } from '@app/core/auth.store';

describe('GapBaselinesPage', () => {
  let component: GapBaselinesPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GapBaselinesPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
      ],
    }).compileComponents();

    const store = TestBed.inject(AuthStore);
    store.setToken('fake-token');

    const fixture = TestBed.createComponent(GapBaselinesPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('baselines signal starts empty', () => {
    expect(component.baselines()).toEqual([]);
  });

  it('assessment signal starts null', () => {
    expect(component.assessment()).toBeNull();
  });

  it('comparison signal starts null', () => {
    expect(component.comparison()).toBeNull();
  });

  it('approveDialogVisible starts false', () => {
    expect(component.approveDialogVisible).toBe(false);
  });

  it('showApproveDialog sets default classification to uso_interno', () => {
    component.showApproveDialog();
    expect(component.approveClassification).toBe('uso_interno');
  });

  it('showApproveDialog sets nature to Emissão inicial when no baselines', () => {
    component.showApproveDialog();
    expect(component.approveNature).toBe('Emissão inicial');
  });
});
