import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Route } from '@angular/router';

import { AuthStore } from '@app/core/auth.store';
import { OrgAwareRouteReuseStrategy } from '@app/core/org-aware-route-reuse.strategy';

function snapshot(routeConfig: Route): ActivatedRouteSnapshot {
  return { routeConfig } as ActivatedRouteSnapshot;
}

describe('OrgAwareRouteReuseStrategy', () => {
  let store: AuthStore;
  let strategy: OrgAwareRouteReuseStrategy;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [OrgAwareRouteReuseStrategy] });
    store = TestBed.inject(AuthStore);
    strategy = TestBed.inject(OrgAwareRouteReuseStrategy);
  });

  it('recria a rota filha atual quando o contexto de organizacao muda', () => {
    const route = { path: 'dashboard' };
    const future = snapshot(route);
    const current = snapshot(route);

    expect(strategy.shouldReuseRoute(future, current)).toBe(true);

    store.setActiveOrg('tenant-a');

    expect(strategy.shouldReuseRoute(future, current)).toBe(false);
    expect(strategy.shouldReuseRoute(future, current)).toBe(true);
  });

  it('mantem o shell principal enquanto a rota filha e recarregada', () => {
    const route = { path: 'app' };

    store.setActiveOrg('tenant-a');

    expect(strategy.shouldReuseRoute(snapshot(route), snapshot(route))).toBe(true);
  });

  it('preserva o comportamento padrao quando a rota muda', () => {
    expect(strategy.shouldReuseRoute(snapshot({ path: 'dashboard' }), snapshot({ path: 'gap-analysis' }))).toBe(false);
  });
});
