import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { RouteReuseStrategy, provideRouter, withRouterConfig } from '@angular/router';
import Material from '@primeuix/themes/material';
import { MessageService } from 'primeng/api';
import { providePrimeNG } from 'primeng/config';

import { errorInterceptor } from '@app/core/error.interceptor';
import { OrgAwareRouteReuseStrategy } from '@app/core/org-aware-route-reuse.strategy';
import { tokenInterceptor } from '@app/core/token.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withRouterConfig({ onSameUrlNavigation: 'reload' })),
    { provide: RouteReuseStrategy, useClass: OrgAwareRouteReuseStrategy },
    provideHttpClient(withInterceptors([tokenInterceptor, errorInterceptor])),
    providePrimeNG({ theme: { preset: Material } }),
    MessageService,
  ],
};
