% Peano arithmetic — Horn clauses WITH function symbols: not Datalog.
%
% datalog.py refuses this file (try it: the error message states the
% boundary).  prolog.py runs it top-down with a depth bound:
%
%   python3 prolog.py programs/peano.pl -q 'add(s(zero), s(s(zero)), X)'
%   python3 prolog.py programs/peano.pl -q 'add(X, Y, s(s(zero)))'
%   python3 prolog.py programs/peano.pl -q 'nat(X)' --max-solutions 5

nat(zero).
nat(s(N)) :- nat(N).

add(zero, N, N).
add(s(M), N, s(R)) :- add(M, N, R).

mult(zero, N, zero).
mult(s(M), N, R) :- mult(M, N, P), add(P, N, R).

lt(zero, s(N)).
lt(s(M), s(N)) :- lt(M, N).
