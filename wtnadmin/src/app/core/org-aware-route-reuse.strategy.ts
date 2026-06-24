import { Injectable, inject } from '@angular/core';
import { ActivatedRouteSnapshot, BaseRouteReuseStrategy } from '@angular/router';

import { AuthStore } from '@app/core/auth.store';

@Injectable()
export class OrgAwareRouteReuseStrategy extends BaseRouteReuseStrategy {
  private readonly authStore = inject(AuthStore);
  private handledOrgVersion = this.authStore.orgContextVersion();

  override shouldReuseRoute(future: ActivatedRouteSnapshot, curr: ActivatedRouteSnapshot): boolean {
    const sameRoute = future.routeConfig === curr.routeConfig;
    const currentVersion = this.authStore.orgContextVersion();
    if (!sameRoute) {
      this.handledOrgVersion = currentVersion;
      return false;
    }
    if (currentVersion !== this.handledOrgVersion && future.routeConfig?.path !== 'app') {
      this.handledOrgVersion = currentVersion;
      return false;
    }
    return true;
  }
}
