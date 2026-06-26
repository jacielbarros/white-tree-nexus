import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { describe, it, expect, beforeEach } from 'vitest';

import { AssetDetailPage } from './asset-detail';
import { AuthStore } from '@app/core/auth.store';

describe('AssetDetailPage', () => {
  let component: AssetDetailPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetDetailPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        MessageService,
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'item-1' }) } } },
      ],
    }).compileComponents();

    TestBed.inject(AuthStore).setToken('fake-token');
    component = TestBed.createComponent(AssetDetailPage).componentInstance;
  });

  it('should create and start loading', () => {
    expect(component).toBeTruthy();
    expect(component.loading()).toBe(true);
  });

  it('maps event types to readable labels', () => {
    expect(component.eventLabel('SCOPE_EXCLUSION')).toBe('Exclusão de escopo');
    expect(component.eventLabel('CRITICALITY_CHANGE')).toBe('Mudança de criticidade');
    expect(component.eventLabel('GAP_LINK')).toBe('Gap vinculado');
  });

  it('maps relationship + cia labels', () => {
    expect(component.relLabel('uses')).toBe('utiliza');
    expect(component.cia('critica')).toBe('Crítica');
    expect(component.cia(null)).toBe('—');
  });

  it('resolves member names from loaded members', () => {
    component.members.set([{ user_id: 'u1', full_name: 'Ana', email: 'ana@x.com' }]);
    expect(component.memberName('u1')).toBe('Ana');
    expect(component.memberName('missing')).toBe('—');
    expect(component.memberName(null)).toBe('—');
  });
});
