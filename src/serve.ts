#!/usr/bin/env node

import { createServer } from './web';

const port = parseInt(process.env.PORT || '3000', 10);
createServer(port);
