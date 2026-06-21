import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { DashboardPage } from './dashboard';

const mockApi = {
  get: vi.fn(),
};
const mockStore = {
  me: vi.fn(() => ({ email: 'a@b.com', memberships: [{ tenant_id: 't1', org_name: 'Org' }] })),
  activeOrgId: vi.fn(() => 't1'),
};

describe('DashboardPage', () => {
  beforeEach(async () => {
    mockApi.get.mockImplementation((path: string) => {
      if (path.includes('gap-assessment/dashboard'))
        return of({ overall_adherence: 0.62, completeness: 0.76, status_distribution: { meets: 45, partial: 20, not_meet: 5, not_applicable: 1, not_filled: 22 } });
      if (path.includes('/soa'))
        return of({ draft_status: 'draft', current_version_id: null, items: [] });
      if (path.includes('/context/overview'))
        return of({ scope: { draft_status: 'approved', current_version_id: 'v1' }, analysis: { draft_status: 'approved' } });
      return of(null);
    });

    await TestBed.configureTestingModule({
      imports: [DashboardPage],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: mockApi },
        { provide: AuthStore, useValue: mockStore },
      ],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(DashboardPage);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render gap adherence from API', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('62%');
  });

  it('should render 3 active module cards', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const cards = fixture.nativeElement.querySelectorAll('.wtn-module-card:not(.wtn-module-card--future)');
    expect(cards.length).toBe(3);
  });

  it('should show org name', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Org');
  });

  it('should render critical gap count', async () => {
    const fixture = TestBed.createComponent(DashboardPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('5');
  });
});
