// Tell React's internal act() check that this is a test environment,
// suppressing the "not configured to support act()" stderr warning.
// @ts-expect-error – IS_REACT_ACT_ENVIRONMENT is a React-internal global
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
