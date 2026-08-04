/**
 * Route parsing shared by the nav bar.
 *
 * The nav bar reads the current tank from the URL rather than from a router
 * hook because it renders outside the `<Routes>` tree. A greedy `/^\/tank\/(.+)$/`
 * captured everything after `/tank/`, so on `/tank/abc/soccer` the navigator
 * received `abc/soccer` as the tank id - and "previous world" then navigated to
 * `/tank/abc/soccer`, a route that does not exist. Match the single path
 * segment the `:tankId` route parameter actually covers.
 */
const TANK_ROUTE = /^\/tank\/([^/]+)(?:\/[^/]*)*\/?$/;

export function parseTankIdFromPath(pathname: string): string | undefined {
    const match = TANK_ROUTE.exec(pathname);
    if (!match) return undefined;
    return decodeURIComponent(match[1]);
}

export function isTankRoute(pathname: string): boolean {
    return pathname === '/' || pathname.startsWith('/tank/');
}
