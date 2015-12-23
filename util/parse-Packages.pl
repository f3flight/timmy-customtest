#!/usr/bin/perl

$/ = undef;
foreach $p (split(/\n{2,}/,<>)) {
    if ( $p =~ /^Package: (.+)/) { print "$1\t" }
    if ( $p =~ /\nVersion: (.+)/) { print "$1\t" }
    if ( $p =~ /\nFilename: (.+)/) { $fn = (split('/',$1))[-1]; print "$fn\n" }
}
