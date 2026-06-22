import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';
import { GapGuidanceAdminPage } from './gap-guidance-admin';

const GUIDANCE = {
  items: [
    {
      seed_item_id: 's1', ref_code: 'A.8.24', referencia: 'ISO/IEC 27001:2022 — A.8.24',
      objetivo: 'Regras de criptografia.', como_avaliar: ['Existe política?'],
      evidencias_esperadas: ['Política de criptografia'], nota: null,
    },
  ],
  legend: {
    status: [{ id: 'l1', code: 'meets', label: 'Atende Totalmente', definition: 'def', order: 3 }],
    priority: [{ id: 'l2', code: 'critical', label: 'Crítica', definition: 'def', order: 1 }],
  },
};

const mockApi = {
  get: vi.fn(() => of(GUIDANCE)),
  put: vi.fn(() => of({ ...GUIDANCE.items[0], objetivo: 'Editado' })),
};

interface View {
  items(): unknown[];
  select(i: unknown): void;
  selected(): { ref_code: string } | null;
  saveItem(): void;
}

describe('GapGuidanceAdminPage', () => {
  let component: GapGuidanceAdminPage;
  let view: View;

  beforeEach(async () => {
    mockApi.get.mockClear();
    mockApi.put.mockClear();
    await TestBed.configureTestingModule({
      imports: [GapGuidanceAdminPage],
      providers: [MessageService, { provide: ApiService, useValue: mockApi }],
    }).compileComponents();

    const fixture = TestBed.createComponent(GapGuidanceAdminPage);
    component = fixture.componentInstance;
    view = component as unknown as View;
    fixture.detectChanges();
  });

  it('should create and load guidance items', () => {
    expect(component).toBeTruthy();
    expect(view.items().length).toBe(1);
    expect(mockApi.get).toHaveBeenCalledWith('/gap/guidance');
  });

  it('saves an edited item via PUT to the correct endpoint', () => {
    view.select(GUIDANCE.items[0]);
    view.saveItem();
    expect(mockApi.put).toHaveBeenCalledWith(
      '/gap/guidance/items/s1',
      expect.objectContaining({ objetivo: 'Regras de criptografia.' }),
    );
  });
});
